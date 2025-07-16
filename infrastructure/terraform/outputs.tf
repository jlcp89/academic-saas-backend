# Academic SaaS Infrastructure Outputs

# Network Information
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of the database subnets"
  value       = aws_subnet.database[*].id
}

# Load Balancer Information
output "backend_alb_dns" {
  description = "DNS name of the backend Application Load Balancer"
  value       = aws_lb.backend.dns_name
}

output "backend_alb_arn" {
  description = "ARN of the backend Application Load Balancer"
  value       = aws_lb.backend.arn
}

output "frontend_alb_dns" {
  description = "DNS name of the frontend Application Load Balancer"
  value       = aws_lb.frontend.dns_name
}

output "frontend_alb_arn" {
  description = "ARN of the frontend Application Load Balancer"
  value       = aws_lb.frontend.arn
}

# Database Information
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "database_username" {
  description = "Database username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

# Redis Information
output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = aws_elasticache_replication_group.main.configuration_endpoint_address
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = aws_elasticache_replication_group.main.port
}

# S3 Information
output "s3_bucket_id" {
  description = "S3 bucket ID"
  value       = aws_s3_bucket.main.id
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = aws_s3_bucket.main.bucket
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.main.arn
}

output "s3_bucket_domain_name" {
  description = "S3 bucket domain name"
  value       = aws_s3_bucket.main.bucket_domain_name
}

# CloudFront Information
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.main.domain_name
}

# Auto Scaling Group Information
output "backend_asg_name" {
  description = "Name of the backend Auto Scaling Group"
  value       = aws_autoscaling_group.backend.name
}

output "frontend_asg_name" {
  description = "Name of the frontend Auto Scaling Group"
  value       = aws_autoscaling_group.frontend.name
}

# Security Group Information
output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "app_security_group_id" {
  description = "ID of the application security group"
  value       = aws_security_group.app.id
}

output "database_security_group_id" {
  description = "ID of the database security group"
  value       = aws_security_group.database.id
}

output "redis_security_group_id" {
  description = "ID of the Redis security group"
  value       = aws_security_group.redis.id
}

# Secrets Manager Information
output "db_secret_arn" {
  description = "ARN of the database password secret"
  value       = aws_secretsmanager_secret.db_password.arn
  sensitive   = true
}

output "redis_secret_arn" {
  description = "ARN of the Redis auth token secret"
  value       = aws_secretsmanager_secret.redis_auth_token.arn
  sensitive   = true
}

# Cost Information
output "monthly_budget_limit" {
  description = "Monthly budget limit"
  value       = var.monthly_budget_limit
}

output "cost_alert_emails" {
  description = "Email addresses for cost alerts"
  value       = var.budget_alert_emails
  sensitive   = true
}

# Environment Information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

# Application URLs
output "application_urls" {
  description = "Application access URLs"
  value = {
    backend_api  = "http://${aws_lb.backend.dns_name}"
    frontend_app = "http://${aws_lb.frontend.dns_name}"
    backend_health = "http://${aws_lb.backend.dns_name}/health"
    frontend_health = "http://${aws_lb.frontend.dns_name}/health"
  }
}

# Infrastructure Costs (Estimated)
output "estimated_monthly_costs" {
  description = "Estimated monthly infrastructure costs"
  value = {
    ec2_instances = "~$15-30/month (Free Tier eligible)"
    rds_database  = "~$13/month (Free Tier eligible)"
    elasticache   = "~$12/month (Free Tier eligible)"
    load_balancers = "~$18/month"
    nat_gateway   = var.use_nat_instance ? "~$4/month (NAT instance)" : "~$32/month (NAT Gateway)"
    storage_cdn   = "~$5-10/month"
    monitoring    = "~$5/month"
    total_estimate = var.use_nat_instance ? "~$70-100/month" : "~$100-130/month"
    free_tier_note = "Most costs covered by AWS Free Tier for first 12 months"
  }
}

# Deployment Information
output "deployment_info" {
  description = "Deployment and access information"
  value = {
    ssh_key_path = "~/.ssh/academic_saas_aws"
    terraform_state = "Stored in S3 with DynamoDB locking"
    monitoring_dashboard = "CloudWatch Console"
    cost_dashboard = "AWS Billing Console"
    deployment_method = "GitHub Actions CI/CD"
  }
}

# Next Steps
output "next_steps" {
  description = "Next steps after infrastructure deployment"
  value = [
    "1. Configure GitHub Actions secrets with AWS credentials",
    "2. Set up database passwords and application secrets",
    "3. Deploy application code via CI/CD pipeline",
    "4. Configure domain name and SSL certificates",
    "5. Set up monitoring alerts and cost budgets",
    "6. Test application functionality and performance",
    "7. Configure backup and disaster recovery procedures"
  ]
}