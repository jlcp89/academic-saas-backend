#!/bin/bash

# NAT Instance Configuration Script
# Configures an EC2 instance to act as a NAT Gateway

# Update system
yum update -y

# Enable IP forwarding
echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf
sysctl -p

# Configure iptables for NAT
iptables -t nat -A POSTROUTING -o eth0 -s ${private_cidr} -j MASQUERADE
iptables -A FORWARD -i eth0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i eth0 -o eth0 -s ${private_cidr} -j ACCEPT

# Save iptables rules
service iptables save

# Start iptables service
chkconfig iptables on
service iptables start

# Configure automatic startup
cat > /etc/rc.local << 'EOF'
#!/bin/bash
# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

# Restore iptables rules
iptables-restore < /etc/sysconfig/iptables
EOF

chmod +x /etc/rc.local

# Install CloudWatch agent for monitoring
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm

# Create CloudWatch agent config
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{
  "metrics": {
    "namespace": "NAT/Instance",
    "metrics_collected": {
      "cpu": {
        "measurement": ["cpu_usage_idle", "cpu_usage_iowait", "cpu_usage_user", "cpu_usage_system"],
        "metrics_collection_interval": 300
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
  }
}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
  -s

echo "NAT Instance configuration completed!"
echo "Instance is now ready to route traffic for private subnets."