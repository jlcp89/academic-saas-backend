# AWS Cost Control and Budget Management

# Cost Allocation Tags for All Resources
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = "Academic-SaaS-Team"
    CostCenter  = "Engineering"
    CreatedBy   = "Terraform"
    LastUpdated = timestamp()
  }
}

# AWS Budgets for Cost Control
resource "aws_budgets_budget" "monthly_cost" {
  name       = "${var.project_name}-${var.environment}-monthly-budget"
  budget_type = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  time_period_start = "2024-01-01_00:00"

  # Cost filters by tags
  cost_filters = {
    TagKey = ["Project"]
    TagValue = [var.project_name]
  }

  # Budget notifications at different thresholds
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 50
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 100
    threshold_type            = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.budget_alert_emails
  }

  tags = local.common_tags
}

# EC2 Instance Budget (Separate tracking)
resource "aws_budgets_budget" "ec2_budget" {
  name         = "${var.project_name}-${var.environment}-ec2-budget"
  budget_type  = "COST"
  limit_amount = var.ec2_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filters = {
    Service = ["Amazon Elastic Compute Cloud - Compute"]
    TagKey  = ["Project"]
    TagValue = [var.project_name]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 80
    threshold_type            = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  tags = local.common_tags
}

# RDS Budget
resource "aws_budgets_budget" "rds_budget" {
  name         = "${var.project_name}-${var.environment}-rds-budget"
  budget_type  = "COST"
  limit_amount = var.rds_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filters = {
    Service = ["Amazon Relational Database Service"]
    TagKey  = ["Project"]
    TagValue = [var.project_name]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                 = 75
    threshold_type            = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  tags = local.common_tags
}

# CloudWatch Cost Anomaly Detection
resource "aws_ce_anomaly_detector" "service_monitor" {
  name         = "${var.project_name}-${var.environment}-anomaly-detector"
  monitor_type = "DIMENSIONAL"

  specification = jsonencode({
    Dimension = "SERVICE"
    MatchOptions = ["EQUALS"]
    Values = ["EC2-Instance", "RDS", "ElastiCache"]
  })

  tags = local.common_tags
}

# Cost Anomaly Subscription
resource "aws_ce_anomaly_subscription" "main" {
  name      = "${var.project_name}-${var.environment}-cost-anomaly"
  frequency = "DAILY"
  
  monitor_arn_list = [
    aws_ce_anomaly_detector.service_monitor.arn,
  ]
  
  subscriber {
    type    = "EMAIL"
    address = var.cost_anomaly_email
  }

  threshold_expression {
    and {
      dimension {
        key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
        values        = [tostring(var.anomaly_threshold)]
        match_options = ["GREATER_THAN_OR_EQUAL"]
      }
    }
  }

  tags = local.common_tags
}

# Lambda Function for Auto-Shutdown of Development Resources
resource "aws_lambda_function" "cost_guard" {
  filename         = data.archive_file.cost_guard_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-cost-guard"
  role            = aws_iam_role.cost_guard_lambda.arn
  handler         = "index.handler"
  runtime         = "python3.9"
  timeout         = 300

  environment {
    variables = {
      ENVIRONMENT = var.environment
      PROJECT_NAME = var.project_name
      MAX_MONTHLY_COST = var.monthly_budget_limit
    }
  }

  tags = local.common_tags
}

# Lambda function code
data "archive_file" "cost_guard_zip" {
  type        = "zip"
  output_path = "/tmp/cost_guard.zip"
  source {
    content = file("${path.module}/lambda/cost_guard.py")
    filename = "index.py"
  }
}

# IAM Role for Cost Guard Lambda
resource "aws_iam_role" "cost_guard_lambda" {
  name = "${var.project_name}-${var.environment}-cost-guard-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for Cost Guard Lambda
resource "aws_iam_role_policy" "cost_guard_lambda" {
  name = "${var.project_name}-${var.environment}-cost-guard-policy"
  role = aws_iam_role.cost_guard_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:StopInstances",
          "ec2:TerminateInstances",
          "rds:DescribeDBInstances",
          "rds:StopDBInstance",
          "elasticache:DescribeReplicationGroups",
          "elasticache:DeleteReplicationGroup",
          "ce:GetCostAndUsage",
          "ce:GetUsageReport"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion" = var.aws_region
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.cost_alerts.arn
      }
    ]
  })
}

# CloudWatch Event Rule to trigger cost monitoring daily
resource "aws_cloudwatch_event_rule" "cost_monitor" {
  name                = "${var.project_name}-${var.environment}-cost-monitor"
  description         = "Trigger cost monitoring lambda daily"
  schedule_expression = "cron(0 8 * * ? *)" # 8 AM UTC daily

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "cost_monitor" {
  rule      = aws_cloudwatch_event_rule.cost_monitor.name
  target_id = "CostGuardLambdaTarget"
  arn       = aws_lambda_function.cost_guard.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_guard.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cost_monitor.arn
}

# SNS Topic for Cost Alerts
resource "aws_sns_topic" "cost_alerts" {
  name = "${var.project_name}-${var.environment}-cost-alerts"

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "cost_alerts_email" {
  count     = length(var.budget_alert_emails)
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.budget_alert_emails[count.index]
}

# CloudWatch Dashboard for Cost Monitoring
resource "aws_cloudwatch_dashboard" "cost_monitoring" {
  dashboard_name = "${var.project_name}-${var.environment}-cost-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", aws_autoscaling_group.backend.name],
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", aws_autoscaling_group.frontend.name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EC2 CPU Utilization"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.id],
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", aws_db_instance.main.id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS Performance"
          period  = 300
        }
      }
    ]
  })
}

# Resource tagging for all resources (applied via locals)
resource "aws_autoscaling_group" "backend_with_tags" {
  # This ensures all ASG instances get proper cost allocation tags
  dynamic "tag" {
    for_each = local.common_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}