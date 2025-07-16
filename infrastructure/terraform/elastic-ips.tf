# Elastic IP Configuration for Stable Addressing

# Elastic IPs for Load Balancers (Static addressing)
resource "aws_eip" "backend_lb" {
  domain = "vpc"
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-backend-lb-eip"
    Type = "LoadBalancer"
  })
}

resource "aws_eip" "frontend_lb" {
  domain = "vpc"
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-frontend-lb-eip"
    Type = "LoadBalancer"
  })
}

# Associate EIPs with Load Balancers
resource "aws_lb" "backend" {
  name               = "${var.project_name}-${var.environment}-backend-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "prod"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-backend-alb"
    Type = "Backend-LoadBalancer"
  })
}

resource "aws_lb" "frontend" {
  name               = "${var.project_name}-${var.environment}-frontend-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "prod"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-frontend-alb"
    Type = "Frontend-LoadBalancer"
  })
}

# Target Groups
resource "aws_lb_target_group" "backend" {
  name     = "${var.project_name}-${var.environment}-backend-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/admin/login/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-backend-tg"
  })
}

resource "aws_lb_target_group" "frontend" {
  name     = "${var.project_name}-${var.environment}-frontend-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-frontend-tg"
  })
}

# Load Balancer Listeners
resource "aws_lb_listener" "backend" {
  load_balancer_arn = aws_lb.backend.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

resource "aws_lb_listener" "frontend" {
  load_balancer_arn = aws_lb.frontend.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# DNS Records pointing to Elastic IPs (when domain is configured)
resource "aws_route53_record" "backend" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.backend.dns_name
    zone_id                = aws_lb.backend.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "frontend" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.frontend.dns_name
    zone_id                = aws_lb.frontend.zone_id
    evaluate_target_health = true
  }
}

data "aws_route53_zone" "main" {
  count = var.domain_name != "" ? 1 : 0
  name  = var.domain_name
}

# Output the load balancer DNS names (stable addresses)
output "backend_url" {
  description = "Backend Load Balancer URL"
  value       = "http://${aws_lb.backend.dns_name}"
}

output "frontend_url" {
  description = "Frontend Load Balancer URL" 
  value       = "http://${aws_lb.frontend.dns_name}"
}

output "backend_eip" {
  description = "Backend Elastic IP"
  value       = aws_eip.backend_lb.public_ip
}

output "frontend_eip" {
  description = "Frontend Elastic IP"
  value       = aws_eip.frontend_lb.public_ip
}