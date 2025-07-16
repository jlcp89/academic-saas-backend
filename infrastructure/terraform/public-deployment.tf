# Alternative: Deploy instances in public subnets (Development only)
# WARNING: Less secure - instances have direct internet access

# Public deployment configuration (use only for development)
resource "aws_launch_template" "backend_public" {
  count = var.use_public_subnets ? 1 : 0
  
  name_prefix   = "${var.project_name}-${var.environment}-backend-public-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.environment_config[var.environment].backend_instance_type
  key_name      = aws_key_pair.main.key_name

  vpc_security_group_ids = [aws_security_group.app_public[0].id]

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2.name
  }

  # Associate public IP
  network_interfaces {
    associate_public_ip_address = true
    security_groups            = [aws_security_group.app_public[0].id]
    delete_on_termination      = true
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
      Name = "${var.project_name}-${var.environment}-backend-public"
      Type = "Backend-Public"
    })
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Security group for public instances (more restrictive)
resource "aws_security_group" "app_public" {
  count       = var.use_public_subnets ? 1 : 0
  name        = "${var.project_name}-${var.environment}-app-public-sg"
  description = "Security group for public app instances"
  vpc_id      = aws_vpc.main.id

  # Allow HTTP/HTTPS from ALB only
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # SSH access from specific IPs only
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-app-public-sg"
  })
}

# Auto Scaling Group for public deployment
resource "aws_autoscaling_group" "backend_public" {
  count = var.use_public_subnets ? 1 : 0
  
  name                = "${var.project_name}-${var.environment}-backend-public-asg"
  vpc_zone_identifier = aws_subnet.public[*].id  # Use public subnets
  target_group_arns   = [aws_lb_target_group.backend.arn]
  health_check_type   = "ELB"
  health_check_grace_period = 300

  min_size         = var.environment_config[var.environment].backend_min_size
  max_size         = var.environment_config[var.environment].backend_max_size
  desired_capacity = var.environment_config[var.environment].backend_desired_capacity

  launch_template {
    id      = aws_launch_template.backend_public[0].id
    version = "$Latest"
  }

  dynamic "tag" {
    for_each = merge(local.common_tags, {
      Name = "${var.project_name}-${var.environment}-backend-public-asg"
      Type = "Public-ASG"
    })
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = false
    }
  }
}