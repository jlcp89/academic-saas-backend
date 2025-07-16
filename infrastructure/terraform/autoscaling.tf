# Launch Template for Backend Servers
resource "aws_launch_template" "backend" {
  name_prefix   = "${var.project_name}-${var.environment}-backend-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.environment_config[var.environment].backend_instance_type
  key_name      = aws_key_pair.main.key_name

  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2.name
  }

  user_data = base64encode(file("${path.module}/user-data-backend-amazonlinux.sh"))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.project_name}-${var.environment}-backend"
      Environment = var.environment
      Type        = "Backend"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Launch Template for Frontend Servers
resource "aws_launch_template" "frontend" {
  name_prefix   = "${var.project_name}-${var.environment}-frontend-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.environment_config[var.environment].frontend_instance_type
  key_name      = aws_key_pair.main.key_name

  vpc_security_group_ids = [aws_security_group.app.id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2.name
  }

  user_data = base64encode(templatefile("${path.module}/user_data/frontend.sh", {
    environment        = var.environment
    project_name      = var.project_name
    backend_alb_dns   = aws_lb.backend.dns_name
    aws_region        = var.aws_region
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.project_name}-${var.environment}-frontend"
      Environment = var.environment
      Type        = "Frontend"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group for Backend
resource "aws_autoscaling_group" "backend" {
  name                = "${var.project_name}-${var.environment}-backend-asg"
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.backend.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = var.environment_config[var.environment].backend_min_size
  max_size         = var.environment_config[var.environment].backend_max_size
  desired_capacity = var.environment_config[var.environment].backend_desired_capacity

  launch_template {
    id      = aws_launch_template.backend.id
    version = "$Latest"
  }

  # Instance refresh configuration for rolling updates
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-backend-asg"
    propagate_at_launch = false
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "Type"
    value               = "Backend"
    propagate_at_launch = true
  }
}

# Auto Scaling Group for Frontend
resource "aws_autoscaling_group" "frontend" {
  name                = "${var.project_name}-${var.environment}-frontend-asg"
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.frontend.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = var.environment_config[var.environment].frontend_min_size
  max_size         = var.environment_config[var.environment].frontend_max_size
  desired_capacity = var.environment_config[var.environment].frontend_desired_capacity

  launch_template {
    id      = aws_launch_template.frontend.id
    version = "$Latest"
  }

  # Instance refresh configuration for rolling updates
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
      instance_warmup        = 300
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-frontend-asg"
    propagate_at_launch = false
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "Type"
    value               = "Frontend"
    propagate_at_launch = true
  }
}

# Auto Scaling Policies for Backend
resource "aws_autoscaling_policy" "backend_scale_up" {
  name                   = "${var.project_name}-${var.environment}-backend-scale-up"
  scaling_adjustment     = 2
  adjustment_type        = "ChangeInCapacity"
  cooldown              = var.scale_up_cooldown
  autoscaling_group_name = aws_autoscaling_group.backend.name
}

resource "aws_autoscaling_policy" "backend_scale_down" {
  name                   = "${var.project_name}-${var.environment}-backend-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = var.scale_down_cooldown
  autoscaling_group_name = aws_autoscaling_group.backend.name
}

# Auto Scaling Policies for Frontend
resource "aws_autoscaling_policy" "frontend_scale_up" {
  name                   = "${var.project_name}-${var.environment}-frontend-scale-up"
  scaling_adjustment     = 2
  adjustment_type        = "ChangeInCapacity"
  cooldown              = var.scale_up_cooldown
  autoscaling_group_name = aws_autoscaling_group.frontend.name
}

resource "aws_autoscaling_policy" "frontend_scale_down" {
  name                   = "${var.project_name}-${var.environment}-frontend-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = var.scale_down_cooldown
  autoscaling_group_name = aws_autoscaling_group.frontend.name
}

# CloudWatch Alarms for Backend Auto Scaling
resource "aws_cloudwatch_metric_alarm" "backend_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-backend-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = var.cpu_target_value
  alarm_description   = "This metric monitors backend CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.backend_scale_up.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.backend.name
  }
}

resource "aws_cloudwatch_metric_alarm" "backend_cpu_low" {
  alarm_name          = "${var.project_name}-${var.environment}-backend-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "20"
  alarm_description   = "This metric monitors backend CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.backend_scale_down.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.backend.name
  }
}

# CloudWatch Alarms for Frontend Auto Scaling
resource "aws_cloudwatch_metric_alarm" "frontend_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-frontend-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = var.cpu_target_value
  alarm_description   = "This metric monitors frontend CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.frontend_scale_up.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.frontend.name
  }
}

resource "aws_cloudwatch_metric_alarm" "frontend_cpu_low" {
  alarm_name          = "${var.project_name}-${var.environment}-frontend-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "20"
  alarm_description   = "This metric monitors frontend CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.frontend_scale_down.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.frontend.name
  }
}

# Data source for Amazon Linux AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Key Pair for EC2 instances
resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-${var.environment}-key"
  public_key = file("/home/jl/.ssh/academic_saas_aws.pub")

  tags = {
    Name        = "${var.project_name}-${var.environment}-key"
    Environment = var.environment
  }
}