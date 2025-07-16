#!/bin/bash

# Academic SaaS Backend Server Setup Script
# This script configures an EC2 instance to run the Django backend

set -e

# Update system
yum update -y

# Install required packages
yum install -y docker git awscli htop

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Add ec2-user to docker group
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Get instance metadata
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

# Configure environment variables
cat > /etc/environment << EOF
# Academic SaaS Backend Configuration
ENVIRONMENT=${environment}
PROJECT_NAME=${project_name}
AWS_REGION=${aws_region}
INSTANCE_ID=$INSTANCE_ID
AVAILABILITY_ZONE=$AZ
PRIVATE_IP=$PRIVATE_IP

# AWS Secrets Manager ARNs
DB_SECRET_ARN=${db_secret_arn}
REDIS_SECRET_ARN=${redis_secret_arn}

# S3 Configuration
AWS_STORAGE_BUCKET_NAME=${s3_bucket_name}
AWS_S3_REGION_NAME=${aws_region}

# Django Configuration
DJANGO_SETTINGS_MODULE=core.settings
PYTHONPATH=/app
EOF

# Source environment
source /etc/environment

# Create application directory
mkdir -p /opt/academic-saas
cd /opt/academic-saas

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWEOF'
{
  "metrics": {
    "namespace": "AcademicSaaS/Backend",
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 300,
        "totalcpu": true
      },
      "disk": {
        "measurement": ["used_percent"],
        "metrics_collection_interval": 300,
        "resources": ["*"]
      },
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 300
      },
      "netstat": {
        "measurement": ["tcp_established", "tcp_time_wait"],
        "metrics_collection_interval": 300
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/academic-saas/logs/django.log",
            "log_group_name": "/academic-saas/${environment}/backend/django",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%d %H:%M:%S"
          },
          {
            "file_path": "/var/log/docker.log",
            "log_group_name": "/academic-saas/${environment}/backend/docker",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%dT%H:%M:%S"
          }
        ]
      }
    }
  }
}
CWEOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s

# Create application startup script
cat > /opt/academic-saas/start-backend.sh << 'STARTEOF'
#!/bin/bash

# Academic SaaS Backend Startup Script
set -e

cd /opt/academic-saas

# Source environment
source /etc/environment

echo "Starting Academic SaaS Backend..."
echo "Environment: $ENVIRONMENT"
echo "Instance ID: $INSTANCE_ID"

# Pull latest application code (will be replaced by CI/CD)
if [ ! -d "academic-saas-backend" ]; then
    echo "Waiting for application deployment..."
    # This will be populated by CI/CD pipeline
    mkdir -p academic-saas-backend
    echo "Placeholder for application code" > academic-saas-backend/README.md
fi

# Get secrets from AWS Secrets Manager
echo "Retrieving database credentials..."
DB_CREDENTIALS=$(aws secretsmanager get-secret-value \
    --secret-id "$DB_SECRET_ARN" \
    --region "$AWS_REGION" \
    --query SecretString --output text)

DB_USERNAME=$(echo $DB_CREDENTIALS | jq -r '.username')
DB_PASSWORD=$(echo $DB_CREDENTIALS | jq -r '.password')

echo "Retrieving Redis credentials..."
REDIS_CREDENTIALS=$(aws secretsmanager get-secret-value \
    --secret-id "$REDIS_SECRET_ARN" \
    --region "$AWS_REGION" \
    --query SecretString --output text)

REDIS_AUTH_TOKEN=$(echo $REDIS_CREDENTIALS | jq -r '.auth_token')
REDIS_ENDPOINT=$(echo $REDIS_CREDENTIALS | jq -r '.endpoint')

# Create environment file for Docker
cat > /opt/academic-saas/.env << ENV_EOF
# Django Configuration
ENVIRONMENT=$ENVIRONMENT
DEBUG=False
SECRET_KEY=placeholder-will-be-set-by-cicd

# Database Configuration
DATABASE_URL=postgresql://$DB_USERNAME:$DB_PASSWORD@database-endpoint:5432/academic_saas_$ENVIRONMENT

# Redis Configuration  
REDIS_URL=redis://:$REDIS_AUTH_TOKEN@$REDIS_ENDPOINT:6379/0

# AWS Configuration
AWS_STORAGE_BUCKET_NAME=$AWS_STORAGE_BUCKET_NAME
AWS_S3_REGION_NAME=$AWS_REGION

# Django Settings
ALLOWED_HOSTS=*
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Logging
DJANGO_LOG_LEVEL=INFO
ENV_EOF

echo "Backend startup script prepared"
echo "Waiting for CI/CD deployment..."

STARTEOF

chmod +x /opt/academic-saas/start-backend.sh

# Create systemd service for backend
cat > /etc/systemd/system/academic-saas-backend.service << 'SERVICEEOF'
[Unit]
Description=Academic SaaS Backend Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/academic-saas/start-backend.sh
ExecStop=/usr/local/bin/docker-compose -f /opt/academic-saas/docker-compose.yml down
WorkingDirectory=/opt/academic-saas
User=root
Group=root

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Enable the service
systemctl daemon-reload
systemctl enable academic-saas-backend.service

# Create health check endpoint
cat > /var/www/html/health << 'HEALTHEOF'
#!/bin/bash

# Backend Health Check
echo "Content-Type: text/plain"
echo ""

# Check if Docker is running
if ! systemctl is-active --quiet docker; then
    echo "UNHEALTHY: Docker service not running"
    exit 1
fi

# Check if backend container is running (after deployment)
if docker ps | grep -q "academic-saas-backend"; then
    echo "HEALTHY: Backend service running"
else
    echo "WAITING: Backend not deployed yet"
fi

exit 0
HEALTHEOF

chmod +x /var/www/html/health

# Install and configure nginx for health checks
yum install -y nginx
systemctl enable nginx
systemctl start nginx

# Configure nginx
cat > /etc/nginx/conf.d/health.conf << 'NGINXEOF'
server {
    listen 8000;
    location /health {
        access_log off;
        alias /var/www/html/health;
        try_files $uri =404;
    }
}
NGINXEOF

systemctl reload nginx

# Create log directory
mkdir -p /opt/academic-saas/logs

# Set up log rotation
cat > /etc/logrotate.d/academic-saas << 'LOGEOF'
/opt/academic-saas/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        systemctl reload academic-saas-backend || true
    endscript
}
LOGEOF

# Install jq for JSON parsing
yum install -y jq

# Create deployment ready marker
echo "Backend instance configured successfully" > /opt/academic-saas/configured
echo "Instance ID: $INSTANCE_ID" >> /opt/academic-saas/configured
echo "Configured at: $(date)" >> /opt/academic-saas/configured

echo "Academic SaaS Backend instance setup completed!"
echo "Instance ready for application deployment via CI/CD"