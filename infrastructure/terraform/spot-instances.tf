# Spot Instance Configuration for Cost Optimization

# Spot Fleet for Development Environment
resource "aws_spot_fleet_request" "dev_backend" {
  count = var.environment == "dev" && var.enable_spot_instances ? 1 : 0

  iam_fleet_role      = aws_iam_role.spot_fleet[0].arn
  allocation_strategy = "diversified"
  target_capacity     = var.environment_config[var.environment].backend_desired_capacity
  spot_price          = "0.10"  # Maximum price willing to pay per hour
  
  # Multiple instance types for better availability
  launch_specification {
    ami                    = data.aws_ami.amazon_linux.id
    instance_type          = "t3.medium"
    key_name              = aws_key_pair.main.key_name
    vpc_security_group_ids = [aws_security_group.app.id]
    subnet_id             = aws_subnet.private[0].id
    availability_zone     = aws_subnet.private[0].availability_zone
    user_data             = base64encode(templatefile("${path.module}/user_data/backend.sh", {
      environment        = var.environment
      project_name      = var.project_name
      db_secret_arn     = aws_secretsmanager_secret.db_password.arn
      redis_secret_arn  = aws_secretsmanager_secret.redis_auth_token.arn
      s3_bucket_name    = aws_s3_bucket.main.bucket
      aws_region        = var.aws_region
    }))

    tags = merge(local.common_tags, {
      Name = "${var.project_name}-${var.environment}-backend-spot"
      Type = "Spot-Backend"
    })
  }

  launch_specification {
    ami                    = data.aws_ami.amazon_linux.id
    instance_type          = "t3.small"
    key_name              = aws_key_pair.main.key_name
    vpc_security_group_ids = [aws_security_group.app.id]
    subnet_id             = aws_subnet.private[1].id
    availability_zone     = aws_subnet.private[1].availability_zone
    user_data             = base64encode(templatefile("${path.module}/user_data/backend.sh", {
      environment        = var.environment
      project_name      = var.project_name
      db_secret_arn     = aws_secretsmanager_secret.db_password.arn
      redis_secret_arn  = aws_secretsmanager_secret.redis_auth_token.arn
      s3_bucket_name    = aws_s3_bucket.main.bucket
      aws_region        = var.aws_region
    }))

    tags = merge(local.common_tags, {
      Name = "${var.project_name}-${var.environment}-backend-spot"
      Type = "Spot-Backend"
    })
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-spot-fleet"
  })
}

# IAM Role for Spot Fleet
resource "aws_iam_role" "spot_fleet" {
  count = var.environment == "dev" && var.enable_spot_instances ? 1 : 0
  name  = "${var.project_name}-${var.environment}-spot-fleet-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "spotfleet.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "spot_fleet" {
  count      = var.environment == "dev" && var.enable_spot_instances ? 1 : 0
  role       = aws_iam_role.spot_fleet[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2SpotFleetTaggingRole"
}

# Mixed Instance Policy for Auto Scaling Groups (On-Demand + Spot)
resource "aws_launch_template" "backend_mixed" {
  count = var.environment != "prod" ? 1 : 0
  
  name_prefix   = "${var.project_name}-${var.environment}-backend-mixed-"
  image_id      = data.aws_ami.amazon_linux.id
  key_name      = aws_key_pair.main.key_name

  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2.name
  }

  user_data = base64encode(templatefile("${path.module}/user_data/backend.sh", {
    environment        = var.environment
    project_name      = var.project_name
    db_secret_arn     = aws_secretsmanager_secret.db_password.arn
    redis_secret_arn  = aws_secretsmanager_secret.redis_auth_token.arn
    s3_bucket_name    = aws_s3_bucket.main.bucket
    aws_region        = var.aws_region
  }))

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${var.project_name}-${var.environment}-backend-mixed"
      Type = "Mixed-Backend"
    })
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group with Mixed Instance Policy
resource "aws_autoscaling_group" "backend_mixed" {
  count = var.environment != "prod" ? 1 : 0
  
  name                = "${var.project_name}-${var.environment}-backend-mixed-asg"
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.backend.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = var.environment_config[var.environment].backend_min_size
  max_size         = var.environment_config[var.environment].backend_max_size
  desired_capacity = var.environment_config[var.environment].backend_desired_capacity

  # Mixed instances policy for cost optimization
  mixed_instances_policy {
    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.backend_mixed[0].id
        version           = "$Latest"
      }

      # Override instance types
      override {
        instance_type = "t3.medium"
      }

      override {
        instance_type = "t3.small"
      }

      override {
        instance_type = "t2.medium"
      }
    }

    # Cost optimization: 70% Spot, 30% On-Demand
    instances_distribution {
      on_demand_base_capacity                  = 1
      on_demand_percentage_above_base_capacity = 30
      spot_allocation_strategy                = "lowest-price"
      spot_instance_pools                     = 3
      spot_max_price                          = "0.10"
    }
  }

  # Instance refresh for updates
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }

  dynamic "tag" {
    for_each = merge(local.common_tags, {
      Name = "${var.project_name}-${var.environment}-backend-mixed-asg"
      Type = "Mixed-ASG"
    })
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = false
    }
  }
}

# Scheduled Actions for Cost Optimization
resource "aws_autoscaling_schedule" "scale_down_evening" {
  count = var.enable_scheduled_scaling && var.environment == "dev" ? 1 : 0

  scheduled_action_name  = "${var.project_name}-${var.environment}-scale-down"
  min_size              = 0
  max_size              = var.environment_config[var.environment].backend_max_size
  desired_capacity      = 0
  recurrence            = var.off_hours_schedule
  autoscaling_group_name = var.enable_spot_instances ? aws_autoscaling_group.backend_mixed[0].name : aws_autoscaling_group.backend.name
}

resource "aws_autoscaling_schedule" "scale_up_morning" {
  count = var.enable_scheduled_scaling && var.environment == "dev" ? 1 : 0

  scheduled_action_name  = "${var.project_name}-${var.environment}-scale-up"
  min_size              = var.environment_config[var.environment].backend_min_size
  max_size              = var.environment_config[var.environment].backend_max_size
  desired_capacity      = var.environment_config[var.environment].backend_desired_capacity
  recurrence            = var.on_hours_schedule
  autoscaling_group_name = var.enable_spot_instances ? aws_autoscaling_group.backend_mixed[0].name : aws_autoscaling_group.backend.name
}

# CloudWatch Alarm for Spot Instance Interruption
resource "aws_cloudwatch_metric_alarm" "spot_interruption" {
  count = var.enable_spot_instances ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-spot-interruption"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "SpotInstanceTerminating"
  namespace           = "AWS/EC2"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when spot instances are being terminated"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    AutoScalingGroupName = var.enable_spot_instances ? aws_autoscaling_group.backend_mixed[0].name : aws_autoscaling_group.backend.name
  }

  tags = local.common_tags
}

# Reserved Instance Recommendations (Cost Explorer)
# Note: aws_ce_rightsizing_recommendation is not available in current AWS provider
# Use AWS Cost Explorer console for RI recommendations

# Cost optimization Lambda for Spot Instance management
resource "aws_lambda_function" "spot_optimizer" {
  count = var.enable_spot_instances ? 1 : 0

  filename         = data.archive_file.spot_optimizer_zip[0].output_path
  function_name    = "${var.project_name}-${var.environment}-spot-optimizer"
  role            = aws_iam_role.spot_optimizer_lambda[0].arn
  handler         = "spot_optimizer.handler"
  runtime         = "python3.9"
  timeout         = 300

  environment {
    variables = {
      ENVIRONMENT = var.environment
      PROJECT_NAME = var.project_name
      ASG_NAME = var.enable_spot_instances ? aws_autoscaling_group.backend_mixed[0].name : aws_autoscaling_group.backend.name
    }
  }

  tags = local.common_tags
}

data "archive_file" "spot_optimizer_zip" {
  count = var.enable_spot_instances ? 1 : 0
  
  type        = "zip"
  output_path = "/tmp/spot_optimizer.zip"
  source {
    content = file("${path.module}/lambda/spot_optimizer.py")
    filename = "spot_optimizer.py"
  }
}

resource "aws_iam_role" "spot_optimizer_lambda" {
  count = var.enable_spot_instances ? 1 : 0
  name  = "${var.project_name}-${var.environment}-spot-optimizer-lambda"

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

resource "aws_iam_role_policy" "spot_optimizer_lambda" {
  count = var.enable_spot_instances ? 1 : 0
  name  = "${var.project_name}-${var.environment}-spot-optimizer-policy"
  role  = aws_iam_role.spot_optimizer_lambda[0].id

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
          "ec2:DescribeSpotInstanceRequests",
          "ec2:DescribeSpotPriceHistory",
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:UpdateAutoScalingGroup",
          "autoscaling:SetDesiredCapacity"
        ]
        Resource = "*"
      }
    ]
  })
}