# High Availability NAT Instance for Production
# Creates NAT instances in multiple AZs with automatic failover

# Launch Template for NAT Instance
resource "aws_launch_template" "nat_instance_ha" {
  count = var.use_nat_instance_ha ? 1 : 0
  
  name_prefix   = "${var.project_name}-${var.environment}-nat-ha-"
  image_id      = data.aws_ami.nat_instance_ha[0].id
  instance_type = var.nat_instance_type
  key_name      = aws_key_pair.main.key_name

  vpc_security_group_ids = [aws_security_group.nat_instance_ha[0].id]

  iam_instance_profile {
    name = aws_iam_instance_profile.nat_instance[0].name
  }

  # Monitoring enabled
  monitoring {
    enabled = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data/nat_instance_ha.sh", {
    private_cidr = var.vpc_cidr
    aws_region   = var.aws_region
    project_name = var.project_name
    environment  = var.environment
  }))

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${var.project_name}-${var.environment}-nat-ha"
      Type = "NAT-HA"
    })
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group for NAT Instance (ensures replacement if failed)
resource "aws_autoscaling_group" "nat_instance_ha" {
  count = var.use_nat_instance_ha ? 3 : 0
  
  name                = "${var.project_name}-${var.environment}-nat-ha-${count.index + 1}"
  vpc_zone_identifier = [aws_subnet.public[count.index].id]
  health_check_type   = "EC2"
  health_check_grace_period = 300

  min_size         = 1
  max_size         = 1
  desired_capacity = 1

  launch_template {
    id      = aws_launch_template.nat_instance_ha[0].id
    version = "$Latest"
  }

  # Tag instances for identification
  tag {
    key                 = "Name"
    value               = "${var.project_name}-${var.environment}-nat-${count.index + 1}"
    propagate_at_launch = true
  }

  tag {
    key                 = "AZ"
    value               = data.aws_availability_zones.available.names[count.index]
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for HA NAT Instance
resource "aws_security_group" "nat_instance_ha" {
  count       = var.use_nat_instance_ha ? 1 : 0
  name        = "${var.project_name}-${var.environment}-nat-ha-sg"
  description = "Security group for HA NAT instances"
  vpc_id      = aws_vpc.main.id

  # Allow all traffic from private subnets
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [for subnet in aws_subnet.private : subnet.cidr_block]
  }

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "udp"
    cidr_blocks = [for subnet in aws_subnet.private : subnet.cidr_block]
  }

  # SSH access for management
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  # Health check from ALB
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-nat-ha-sg"
  })
}

# Elastic IPs for NAT Instances
resource "aws_eip" "nat_instance_ha" {
  count  = var.use_nat_instance_ha ? 3 : 0
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-nat-ha-eip-${count.index + 1}"
    AZ   = data.aws_availability_zones.available.names[count.index]
  })

  depends_on = [aws_internet_gateway.main]
}

# Lambda function for EIP management and failover
resource "aws_lambda_function" "nat_failover" {
  count = var.use_nat_instance_ha ? 1 : 0
  
  filename         = data.archive_file.nat_failover_zip[0].output_path
  function_name    = "${var.project_name}-${var.environment}-nat-failover"
  role            = aws_iam_role.nat_failover_lambda[0].arn
  handler         = "index.handler"
  runtime         = "python3.9"
  timeout         = 300

  environment {
    variables = {
      PROJECT_NAME = var.project_name
      ENVIRONMENT  = var.environment
      AWS_REGION   = var.aws_region
    }
  }

  tags = local.common_tags
}

# Lambda code for NAT failover
data "archive_file" "nat_failover_zip" {
  count = var.use_nat_instance_ha ? 1 : 0
  
  type        = "zip"
  output_path = "/tmp/nat_failover.zip"
  source {
    content = file("${path.module}/lambda/nat_failover.py")
    filename = "index.py"
  }
}

# IAM Role for NAT failover Lambda
resource "aws_iam_role" "nat_failover_lambda" {
  count = var.use_nat_instance_ha ? 1 : 0
  name  = "${var.project_name}-${var.environment}-nat-failover-lambda"

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

# IAM Policy for NAT failover
resource "aws_iam_role_policy" "nat_failover_lambda" {
  count = var.use_nat_instance_ha ? 1 : 0
  name  = "${var.project_name}-${var.environment}-nat-failover-policy"
  role  = aws_iam_role.nat_failover_lambda[0].id

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
          "ec2:DescribeAddresses",
          "ec2:AssociateAddress",
          "ec2:DisassociateAddress",
          "ec2:DescribeRouteTables",
          "ec2:CreateRoute",
          "ec2:ReplaceRoute",
          "ec2:DeleteRoute",
          "autoscaling:DescribeAutoScalingGroups",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}

# CloudWatch Event Rule for NAT health monitoring
resource "aws_cloudwatch_event_rule" "nat_health_check" {
  count               = var.use_nat_instance_ha ? 1 : 0
  name                = "${var.project_name}-${var.environment}-nat-health-check"
  description         = "Monitor NAT instance health"
  schedule_expression = "rate(2 minutes)"

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "nat_health_check" {
  count     = var.use_nat_instance_ha ? 1 : 0
  rule      = aws_cloudwatch_event_rule.nat_health_check[0].name
  target_id = "NATHealthCheckLambdaTarget"
  arn       = aws_lambda_function.nat_failover[0].arn
}

resource "aws_lambda_permission" "allow_cloudwatch_nat" {
  count         = var.use_nat_instance_ha ? 1 : 0
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.nat_failover[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.nat_health_check[0].arn
}

# Route tables for HA NAT instances
resource "aws_route_table" "private_nat_ha" {
  count  = var.use_nat_instance_ha ? 3 : 0
  vpc_id = aws_vpc.main.id

  # Routes will be managed by Lambda function
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-rt-nat-ha-${count.index + 1}"
    AZ   = data.aws_availability_zones.available.names[count.index]
  })
}

resource "aws_route_table_association" "private_nat_ha" {
  count          = var.use_nat_instance_ha ? 3 : 0
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private_nat_ha[count.index].id
}

# AMI for HA NAT Instance
data "aws_ami" "nat_instance_ha" {
  count       = var.use_nat_instance_ha ? 1 : 0
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

# IAM Instance Profile for NAT Instance
resource "aws_iam_instance_profile" "nat_instance" {
  count = var.use_nat_instance_ha ? 1 : 0
  name  = "${var.project_name}-${var.environment}-nat-instance-profile"
  role  = aws_iam_role.nat_instance[0].name
}

resource "aws_iam_role" "nat_instance" {
  count = var.use_nat_instance_ha ? 1 : 0
  name  = "${var.project_name}-${var.environment}-nat-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "nat_instance" {
  count = var.use_nat_instance_ha ? 1 : 0
  name  = "${var.project_name}-${var.environment}-nat-instance-policy"
  role  = aws_iam_role.nat_instance[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeAddresses",
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}