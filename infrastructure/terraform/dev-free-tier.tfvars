# Development Environment - Free Tier Configuration
environment = "dev"
project_name = "academic-saas"
aws_region = "us-east-1"

# Free Tier Instance Types
environment_config = {
  dev = {
    backend_instance_type     = "t3.micro"      # FREE: 750 hours/month
    frontend_instance_type    = "t3.micro"     # FREE: 750 hours/month
    db_instance_class        = "db.t3.micro"   # FREE: 750 hours/month
    redis_node_type          = "cache.t3.micro" # FREE: 750 hours/month
    backend_min_size         = 1
    backend_max_size         = 2
    backend_desired_capacity = 1
    frontend_min_size        = 1
    frontend_max_size        = 2
    frontend_desired_capacity = 1
  }
}

# Cost Control for Development
monthly_budget_limit = 50        # Low budget for dev
ec2_budget_limit = 20
rds_budget_limit = 15

# Free Tier Database Configuration
db_allocated_storage = 20        # FREE: Up to 20GB
db_max_allocated_storage = 20    # Keep within free tier

# Enable cost optimization features
enable_spot_instances = false    # Use on-demand for stability in dev
enable_scheduled_scaling = true  # Scale down nights/weekends
s3_lifecycle_enabled = true

# Development-specific settings
vpc_cidr = "10.0.0.0/16"

# Budget alerts
budget_alert_emails = ["admin@yourdomain.com"]
cost_anomaly_email = "admin@yourdomain.com"
anomaly_threshold = 25           # Alert if cost exceeds $25

# S3 bucket name (will be auto-generated with random suffix)
s3_bucket_name = ""

# NAT Gateway alternatives for cost optimization
use_nat_instance = true      # Use NAT instance instead of gateway (87% savings)
use_public_subnets = false   # Keep private subnets for security

# SSH access (restrict in production)
allowed_ssh_cidrs = ["0.0.0.0/0"]

# Elastic IPs for stable addressing
# Cost breakdown:
# - 2x Elastic IPs: $2/month
# - NAT Instance: $3.80/month (t3.nano)
# Total: ~$7/month (vs $35/month with NAT Gateway)