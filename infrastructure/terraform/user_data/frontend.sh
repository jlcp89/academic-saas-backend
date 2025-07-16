#!/bin/bash

# Academic SaaS Frontend Server Setup Script
# This script configures an EC2 instance to run the Next.js frontend

set -e

# Update system
yum update -y

# Install required packages
yum install -y docker git awscli htop nginx

# Install Node.js 18 (LTS)
curl -fsSL https://rpm.nodesource.com/setup_18.x | bash -
yum install -y nodejs

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
# Academic SaaS Frontend Configuration
ENVIRONMENT=${environment}
PROJECT_NAME=${project_name}
AWS_REGION=${aws_region}
INSTANCE_ID=$INSTANCE_ID
AVAILABILITY_ZONE=$AZ
PRIVATE_IP=$PRIVATE_IP

# Backend API Configuration
BACKEND_ALB_DNS=${backend_alb_dns}
NEXT_PUBLIC_API_URL=http://${backend_alb_dns}

# Next.js Configuration
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
EOF

# Source environment
source /etc/environment

# Create application directory
mkdir -p /opt/academic-saas-frontend
cd /opt/academic-saas-frontend

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWEOF'
{
  "metrics": {
    "namespace": "AcademicSaaS/Frontend",
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
            "file_path": "/opt/academic-saas-frontend/logs/nextjs.log",
            "log_group_name": "/academic-saas/${environment}/frontend/nextjs",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y-%m-%d %H:%M:%S"
          },
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "/academic-saas/${environment}/frontend/nginx-access",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%d/%b/%Y:%H:%M:%S"
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "/academic-saas/${environment}/frontend/nginx-error",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%Y/%m/%d %H:%M:%S"
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
cat > /opt/academic-saas-frontend/start-frontend.sh << 'STARTEOF'
#!/bin/bash

# Academic SaaS Frontend Startup Script
set -e

cd /opt/academic-saas-frontend

# Source environment
source /etc/environment

echo "Starting Academic SaaS Frontend..."
echo "Environment: $ENVIRONMENT"
echo "Instance ID: $INSTANCE_ID"
echo "Backend API: $NEXT_PUBLIC_API_URL"

# Pull latest application code (will be replaced by CI/CD)
if [ ! -d "academic-saas-frontend" ]; then
    echo "Waiting for application deployment..."
    # This will be populated by CI/CD pipeline
    mkdir -p academic-saas-frontend
    echo "Placeholder for frontend application" > academic-saas-frontend/README.md
fi

# Create environment file for Next.js
cat > /opt/academic-saas-frontend/.env.local << ENV_EOF
# Next.js Configuration
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1

# API Configuration
NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# NextAuth Configuration (will be set by CI/CD)
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=placeholder-will-be-set-by-cicd

# Environment
ENVIRONMENT=$ENVIRONMENT
ENV_EOF

echo "Frontend startup script prepared"
echo "Waiting for CI/CD deployment..."

STARTEOF

chmod +x /opt/academic-saas-frontend/start-frontend.sh

# Create systemd service for frontend
cat > /etc/systemd/system/academic-saas-frontend.service << 'SERVICEEOF'
[Unit]
Description=Academic SaaS Frontend Service
After=docker.service nginx.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/academic-saas-frontend/start-frontend.sh
ExecStop=/usr/local/bin/docker-compose -f /opt/academic-saas-frontend/docker-compose.yml down
WorkingDirectory=/opt/academic-saas-frontend
User=root
Group=root

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Enable the service
systemctl daemon-reload
systemctl enable academic-saas-frontend.service

# Configure Nginx as reverse proxy
cat > /etc/nginx/nginx.conf << 'NGINXEOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;

    # Upstream for Next.js application
    upstream nextjs_backend {
        server 127.0.0.1:3000;
    }

    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;
        client_max_body_size 50M;

        # Security headers
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # Health check endpoint
        location /health {
            access_log off;
            add_header Content-Type text/plain;
            return 200 "Frontend Healthy\n";
        }

        # Static files caching
        location /_next/static/ {
            proxy_pass http://nextjs_backend;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Main application
        location / {
            limit_req zone=general burst=20 nodelay;
            
            proxy_pass http://nextjs_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }
    }
}
NGINXEOF

# Start and enable nginx
systemctl enable nginx
systemctl start nginx

# Create health check script
cat > /var/www/html/health << 'HEALTHEOF'
#!/bin/bash

# Frontend Health Check
echo "Content-Type: text/plain"
echo ""

# Check if nginx is running
if ! systemctl is-active --quiet nginx; then
    echo "UNHEALTHY: Nginx service not running"
    exit 1
fi

# Check if frontend application is running (after deployment)
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "HEALTHY: Frontend service running"
else
    echo "WAITING: Frontend not deployed yet"
fi

exit 0
HEALTHEOF

chmod +x /var/www/html/health

# Create log directory
mkdir -p /opt/academic-saas-frontend/logs

# Set up log rotation
cat > /etc/logrotate.d/academic-saas-frontend << 'LOGEOF'
/opt/academic-saas-frontend/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
    postrotate
        systemctl reload academic-saas-frontend || true
    endscript
}

/var/log/nginx/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 644 nginx nginx
    postrotate
        systemctl reload nginx
    endscript
}
LOGEOF

# Create deployment ready marker
echo "Frontend instance configured successfully" > /opt/academic-saas-frontend/configured
echo "Instance ID: $INSTANCE_ID" >> /opt/academic-saas-frontend/configured
echo "Backend API: $NEXT_PUBLIC_API_URL" >> /opt/academic-saas-frontend/configured
echo "Configured at: $(date)" >> /opt/academic-saas-frontend/configured

echo "Academic SaaS Frontend instance setup completed!"
echo "Instance ready for application deployment via CI/CD"
echo "Nginx configured as reverse proxy on port 80"