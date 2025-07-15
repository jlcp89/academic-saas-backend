# Cost Control Variables

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 500
  validation {
    condition     = var.monthly_budget_limit > 0
    error_message = "Monthly budget limit must be greater than 0."
  }
}

variable "ec2_budget_limit" {
  description = "EC2-specific monthly budget limit in USD"
  type        = number
  default     = 200
}

variable "rds_budget_limit" {
  description = "RDS-specific monthly budget limit in USD"
  type        = number
  default     = 150
}

variable "budget_alert_emails" {
  description = "List of email addresses to receive budget alerts"
  type        = list(string)
  default     = ["admin@yourdomain.com"]
  validation {
    condition     = length(var.budget_alert_emails) > 0
    error_message = "At least one email address must be provided for budget alerts."
  }
}

variable "cost_anomaly_email" {
  description = "Email address for cost anomaly alerts"
  type        = string
  default     = "admin@yourdomain.com"
}

variable "anomaly_threshold" {
  description = "Cost anomaly threshold in USD"
  type        = number
  default     = 100
}

# Environment-specific cost limits
variable "environment_cost_limits" {
  description = "Environment-specific cost limits"
  type = map(object({
    monthly_budget  = number
    ec2_budget     = number
    rds_budget     = number
    auto_shutdown  = bool
    scale_down     = bool
  }))
  default = {
    dev = {
      monthly_budget = 200
      ec2_budget     = 100
      rds_budget     = 50
      auto_shutdown  = true
      scale_down     = true
    }
    staging = {
      monthly_budget = 500
      ec2_budget     = 300
      rds_budget     = 150
      auto_shutdown  = false
      scale_down     = true
    }
    prod = {
      monthly_budget = 2000
      ec2_budget     = 1200
      rds_budget     = 600
      auto_shutdown  = false
      scale_down     = false
    }
  }
}

# Cost optimization settings
variable "enable_spot_instances" {
  description = "Enable Spot instances for development environments"
  type        = bool
  default     = true
}

variable "enable_scheduled_scaling" {
  description = "Enable scheduled scaling for predictable workloads"
  type        = bool
  default     = true
}

variable "off_hours_schedule" {
  description = "Schedule for scaling down during off-hours (cron format)"
  type        = string
  default     = "0 18 * * 1-5"  # 6 PM on weekdays
}

variable "on_hours_schedule" {
  description = "Schedule for scaling up during business hours (cron format)"
  type        = string
  default     = "0 8 * * 1-5"   # 8 AM on weekdays
}

# Reserved Instance recommendations
variable "enable_ri_recommendations" {
  description = "Enable Reserved Instance cost optimization recommendations"
  type        = bool
  default     = true
}

# S3 cost optimization
variable "s3_lifecycle_enabled" {
  description = "Enable S3 lifecycle policies for cost optimization"
  type        = bool
  default     = true
}

variable "s3_transition_to_ia_days" {
  description = "Days after which objects transition to IA storage class"
  type        = number
  default     = 30
}

variable "s3_transition_to_glacier_days" {
  description = "Days after which objects transition to Glacier"
  type        = number
  default     = 90
}

variable "s3_expiration_days" {
  description = "Days after which objects are deleted (0 = never)"
  type        = number
  default     = 365
}