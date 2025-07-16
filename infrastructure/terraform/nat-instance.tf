# NAT Instance Alternative (Cost-effective for development)

# Security Group for NAT Instance
resource "aws_security_group" "nat_instance" {
  count       = var.use_nat_instance ? 1 : 0
  name        = "${var.project_name}-${var.environment}-nat-instance-sg"
  description = "Security group for NAT instance"
  vpc_id      = aws_vpc.main.id

  # Allow HTTP/HTTPS outbound
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all traffic from private subnets
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [for subnet in aws_subnet.private : subnet.cidr_block]
  }

  # Allow SSH from bastion (optional)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-nat-instance-sg"
  })
}

# NAT Instance (t3.nano - $3.80/month)
resource "aws_instance" "nat_instance" {
  count                  = var.use_nat_instance ? 1 : 0
  ami                   = data.aws_ami.nat_instance[0].id
  instance_type         = "t3.nano"  # Cheapest option
  key_name              = aws_key_pair.main.key_name
  vpc_security_group_ids = [aws_security_group.nat_instance[0].id]
  subnet_id             = aws_subnet.public[0].id
  source_dest_check     = false  # Essential for NAT functionality

  # User data to configure NAT
  user_data = base64encode(templatefile("${path.module}/user_data/nat_instance.sh", {
    private_cidr = var.vpc_cidr
  }))

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-nat-instance"
    Type = "NAT"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for NAT Instance
resource "aws_eip" "nat_instance" {
  count    = var.use_nat_instance ? 1 : 0
  instance = aws_instance.nat_instance[0].id
  domain   = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-nat-instance-eip"
  })

  depends_on = [aws_internet_gateway.main]
}

# AMI for NAT Instance
data "aws_ami" "nat_instance" {
  count       = var.use_nat_instance ? 1 : 0
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

# Update route tables to use NAT Instance instead of NAT Gateway
resource "aws_route_table" "private_nat_instance" {
  count  = var.use_nat_instance ? 3 : 0
  vpc_id = aws_vpc.main.id

  route {
    cidr_block           = "0.0.0.0/0"
    network_interface_id = aws_instance.nat_instance[0].primary_network_interface_id
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-rt-nat-instance-${count.index + 1}"
  })
}

resource "aws_route_table_association" "private_nat_instance" {
  count          = var.use_nat_instance ? 3 : 0
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private_nat_instance[count.index].id
}

# NAT Gateway creation is handled in main.tf
# This block is commented to avoid duplication
# resource "aws_nat_gateway" "main" is defined in main.tf