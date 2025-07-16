#!/bin/bash

# High Availability NAT Instance Configuration
# Enhanced version with monitoring and auto-recovery

# Update system
yum update -y

# Install required packages
yum install -y awscli iptables-services htop

# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
echo 'net.ipv4.conf.eth0.send_redirects = 0' >> /etc/sysctl.conf
sysctl -p

# Get instance metadata
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
VPC_CIDR="${private_cidr}"

# Configure iptables for NAT with logging
iptables -t nat -A POSTROUTING -o eth0 -s $VPC_CIDR -j MASQUERADE
iptables -A FORWARD -i eth0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o eth0 -s $VPC_CIDR -j ACCEPT

# Log NAT traffic for monitoring
iptables -A FORWARD -j LOG --log-prefix "NAT-FORWARD: " --log-level 4

# Save iptables rules
service iptables save
systemctl enable iptables
systemctl start iptables

# Configure NAT health check endpoint
cat > /var/www/html/health << 'EOF'
#!/bin/bash
# NAT Health Check Script

# Check if IP forwarding is enabled
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
    echo "UNHEALTHY: IP forwarding disabled"
    exit 1
fi

# Check if iptables NAT rules exist
if ! iptables -t nat -L POSTROUTING | grep -q MASQUERADE; then
    echo "UNHEALTHY: NAT rules missing"
    exit 1
fi

# Check internet connectivity
if ! ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
    echo "UNHEALTHY: No internet connectivity"
    exit 1
fi

echo "HEALTHY: NAT instance operational"
exit 0
EOF

chmod +x /var/www/html/health

# Install and configure nginx for health checks
yum install -y nginx
systemctl enable nginx
systemctl start nginx

# Configure nginx for health endpoint
cat > /etc/nginx/conf.d/health.conf << 'EOF'
server {
    listen 80;
    location /health {
        access_log off;
        add_header Content-Type text/plain;
        return 200 "NAT Instance Healthy\n";
    }
    
    location /health/detailed {
        access_log off;
        add_header Content-Type text/plain;
        alias /var/www/html/health;
        try_files $uri =404;
    }
}
EOF

systemctl reload nginx

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "metrics": {
    "namespace": "NAT/Instance",
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 60,
        "totalcpu": true
      },
      "disk": {
        "measurement": ["used_percent"],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      },
      "netstat": {
        "measurement": ["tcp_established", "tcp_time_wait"],
        "metrics_collection_interval": 60
      },
      "net": {
        "measurement": ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv"],
        "metrics_collection_interval": 60,
        "resources": ["eth0"]
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "/${project_name}/${environment}/nat/system",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%b %d %H:%M:%S"
          },
          {
            "file_path": "/var/log/iptables.log",
            "log_group_name": "/${project_name}/${environment}/nat/iptables",
            "log_stream_name": "{instance_id}",
            "timestamp_format": "%b %d %H:%M:%S"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s

# Create monitoring script
cat > /usr/local/bin/nat-monitor.sh << 'EOF'
#!/bin/bash

# NAT Instance Monitoring Script
# Runs every minute via cron

INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)

# Check NAT functionality
NAT_STATUS="healthy"
ERROR_MSG=""

# Test IP forwarding
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
    NAT_STATUS="unhealthy"
    ERROR_MSG="IP forwarding disabled"
fi

# Test iptables rules
if ! iptables -t nat -L POSTROUTING | grep -q MASQUERADE; then
    NAT_STATUS="unhealthy"
    ERROR_MSG="NAT rules missing"
fi

# Test internet connectivity
if ! ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
    NAT_STATUS="unhealthy"
    ERROR_MSG="No internet connectivity"
fi

# Send custom metric to CloudWatch
aws cloudwatch put-metric-data \
  --region ${aws_region} \
  --namespace "NAT/Instance" \
  --metric-data MetricName=Health,Value=$([ "$NAT_STATUS" = "healthy" ] && echo 1 || echo 0),Unit=Count,Dimensions=InstanceId=$INSTANCE_ID,AvailabilityZone=$AZ

# Log status
echo "$(date): NAT Status: $NAT_STATUS $ERROR_MSG" >> /var/log/nat-monitor.log

# Auto-recovery: restart services if unhealthy
if [ "$NAT_STATUS" = "unhealthy" ]; then
    echo "$(date): Attempting NAT recovery..." >> /var/log/nat-monitor.log
    
    # Re-enable IP forwarding
    echo 1 > /proc/sys/net/ipv4/ip_forward
    
    # Restore iptables rules
    systemctl restart iptables
    
    # Send alert
    aws sns publish \
      --region ${aws_region} \
      --topic-arn "arn:aws:sns:${aws_region}:$(aws sts get-caller-identity --query Account --output text):${project_name}-${environment}-alerts" \
      --message "NAT Instance $INSTANCE_ID in $AZ is unhealthy: $ERROR_MSG. Auto-recovery attempted." \
      --subject "NAT Instance Health Alert" || true
fi
EOF

chmod +x /usr/local/bin/nat-monitor.sh

# Set up cron job for monitoring
echo "* * * * * /usr/local/bin/nat-monitor.sh" | crontab -

# Create startup script
cat > /etc/rc.local << 'EOF'
#!/bin/bash

# NAT Instance startup script
echo 1 > /proc/sys/net/ipv4/ip_forward

# Wait for network to be ready
sleep 30

# Try to associate Elastic IP
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)

# Get the appropriate EIP for this AZ
# This will be handled by the Lambda function

# Start monitoring
/usr/local/bin/nat-monitor.sh

exit 0
EOF

chmod +x /etc/rc.local

# Configure log rotation for NAT logs
cat > /etc/logrotate.d/nat << 'EOF'
/var/log/nat-monitor.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}

/var/log/iptables.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF

# Initial monitoring run
/usr/local/bin/nat-monitor.sh

echo "NAT Instance HA configuration completed!"
echo "Instance ID: $INSTANCE_ID"
echo "Availability Zone: $AZ"
echo "Health endpoint: http://<instance-ip>/health"
echo "Monitoring: CloudWatch metrics enabled"
echo "Auto-recovery: Enabled via cron job"