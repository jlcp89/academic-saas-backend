# Production Environment - First Client (1 School, 100 Students)
environment = "prod"
project_name = "academic-saas"
aws_region = "us-east-1"

# Starter Production Instance Types
environment_config = {
  prod = {
    backend_instance_type     = "t3.small"      # $15/month - handles 100 concurrent users
    frontend_instance_type    = "t3.small"     # $15/month - serves static content
    db_instance_class        = "db.t3.small"   # $25/month - sufficient for 100 students
    redis_node_type          = "cache.t3.small" # $20/month - caching for performance
    backend_min_size         = 1
    backend_max_size         = 3               # Auto-scale up during peak hours
    backend_desired_capacity = 2              # 2 instances for high availability
    frontend_min_size        = 1
    frontend_max_size        = 2
    frontend_desired_capacity = 1
  }
}

# Production Cost Control
monthly_budget_limit = 200       # Reasonable for first client
ec2_budget_limit = 100
rds_budget_limit = 60

# Production Database Configuration
db_allocated_storage = 50        # Start with 50GB
db_max_allocated_storage = 200   # Auto-expand up to 200GB
backup_retention_period = 7     # 7 days backup
multi_az = true                 # High availability

# Production optimizations
enable_spot_instances = false    # Use on-demand for reliability
enable_scheduled_scaling = false # Keep running 24/7
s3_lifecycle_enabled = true

# Production VPC
vpc_cidr = "10.1.0.0/16"

# Production alerts
budget_alert_emails = ["admin@yourdomain.com", "alerts@yourdomain.com"]
cost_anomaly_email = "admin@yourdomain.com"
anomaly_threshold = 100

# Production domain and SSL
domain_name = "yourdomain.com"
# certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/your-cert-arn"

# Production S3 bucket
s3_bucket_name = "academic-saas-prod-static"

# NAT Configuration for Production Cost Optimization
use_nat_instance_ha = true    # Use HA NAT instances instead of NAT Gateway (75% cost savings)
nat_instance_type = "t3.small"  # Sufficient for 100 students
use_nat_instance = false     # Use HA version for production
use_public_subnets = false   # Keep security with private subnets