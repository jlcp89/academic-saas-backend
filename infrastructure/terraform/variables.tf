# Project Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "academic-saas"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# RDS Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "RDS maximum allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "academic_saas"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "academic_user"
}

# Redis Configuration
variable "redis_node_type" {
  description = "Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of Redis cache nodes"
  type        = number
  default     = 3
}

# EC2 Configuration
variable "backend_instance_type" {
  description = "EC2 instance type for backend servers"
  type        = string
  default     = "t3.medium"
}

variable "frontend_instance_type" {
  description = "EC2 instance type for frontend servers"
  type        = string
  default     = "t3.small"
}

variable "backend_min_size" {
  description = "Minimum number of backend instances"
  type        = number
  default     = 2
}

variable "backend_max_size" {
  description = "Maximum number of backend instances"
  type        = number
  default     = 10
}

variable "backend_desired_capacity" {
  description = "Desired number of backend instances"
  type        = number
  default     = 3
}

variable "frontend_min_size" {
  description = "Minimum number of frontend instances"
  type        = number
  default     = 2
}

variable "frontend_max_size" {
  description = "Maximum number of frontend instances"
  type        = number
  default     = 8
}

variable "frontend_desired_capacity" {
  description = "Desired number of frontend instances"
  type        = number
  default     = 2
}

# Auto Scaling Configuration
variable "cpu_target_value" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
}

variable "scale_up_cooldown" {
  description = "Scale up cooldown period in seconds"
  type        = number
  default     = 300
}

variable "scale_down_cooldown" {
  description = "Scale down cooldown period in seconds"
  type        = number
  default     = 300
}

# S3 Configuration
variable "s3_bucket_name" {
  description = "S3 bucket name for static/media files"
  type        = string
  default     = ""
}

# Domain Configuration
variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# SSL Certificate
variable "certificate_arn" {
  description = "ARN of SSL certificate in ACM"
  type        = string
  default     = ""
}

# Environment-specific overrides
# Development mode toggle
variable "dev_minimal_mode" {
  description = "Enable minimal development mode (single instance, no load balancer)"
  type        = bool
  default     = true
}

variable "environment_config" {
  description = "Environment-specific configuration"
  type = map(object({
    backend_instance_type     = string
    frontend_instance_type    = string
    db_instance_class        = string
    redis_node_type          = string
    backend_min_size         = number
    backend_max_size         = number
    backend_desired_capacity = number
    frontend_min_size        = number
    frontend_max_size        = number
    frontend_desired_capacity = number
  }))
  default = {
    dev = {
      backend_instance_type     = "t2.micro"    # Free tier eligible
      frontend_instance_type    = "t2.micro"    # Free tier eligible
      db_instance_class        = "db.t3.micro"  # Free tier eligible
      redis_node_type          = "cache.t3.micro"
      backend_min_size         = 1
      backend_max_size         = 1
      backend_desired_capacity = 1
      frontend_min_size        = 1
      frontend_max_size        = 1
      frontend_desired_capacity = 1
    }
    staging = {
      backend_instance_type     = "t3.medium"
      frontend_instance_type    = "t3.small"
      db_instance_class        = "db.t3.small"
      redis_node_type          = "cache.t3.small"
      backend_min_size         = 2
      backend_max_size         = 5
      backend_desired_capacity = 2
      frontend_min_size        = 1
      frontend_max_size        = 3
      frontend_desired_capacity = 2
    }
    prod = {
      backend_instance_type     = "t3.large"
      frontend_instance_type    = "t3.medium"
      db_instance_class        = "db.r5.large"
      redis_node_type          = "cache.r5.large"
      backend_min_size         = 3
      backend_max_size         = 20
      backend_desired_capacity = 5
      frontend_min_size        = 2
      frontend_max_size        = 15
      frontend_desired_capacity = 3
    }
  }
}