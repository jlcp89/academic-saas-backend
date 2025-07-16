# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id

  tags = {
    Name        = "${var.project_name}-db-subnet-group"
    Environment = var.environment
  }
}

# RDS Parameter Group for Performance Optimization
resource "aws_db_parameter_group" "main" {
  family = "postgres15"
  name   = "${var.project_name}-${var.environment}-pg15"

  # Performance parameters for high concurrency
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "max_connections"
    value        = "500"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4}"
  }

  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory*3/4}"
  }

  parameter {
    name         = "work_mem"
    value        = "4096"
    apply_method = "immediate"
  }

  parameter {
    name         = "maintenance_work_mem"
    value        = "65536"
    apply_method = "immediate"
  }

  parameter {
    name         = "checkpoint_completion_target"
    value        = "0.9"
    apply_method = "immediate"
  }

  parameter {
    name         = "wal_buffers"
    value        = "16384"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "default_statistics_target"
    value        = "100"
    apply_method = "immediate"
  }

  parameter {
    name         = "random_page_cost"
    value        = "1.1"
    apply_method = "immediate"
  }

  parameter {
    name         = "effective_io_concurrency"
    value        = "200"
    apply_method = "immediate"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-pg15"
    Environment = var.environment
  }
}

# Generate random password for RDS
resource "random_password" "db_password" {
  length  = 16
  special = true
}

# Store password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name        = "${var.project_name}-${var.environment}-db-password"
  description = "Database password for ${var.project_name} ${var.environment}"

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-password"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
  })
}

# RDS Instance with Multi-AZ for High Availability
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-db"

  # Engine configuration
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.environment_config[var.environment].db_instance_class

  # Storage configuration
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  # High availability configuration
  multi_az               = var.environment == "prod" ? true : false
  backup_retention_period = var.environment == "prod" ? 7 : 1
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  # Performance configuration
  parameter_group_name = aws_db_parameter_group.main.name
  monitoring_interval  = 60
  monitoring_role_arn  = aws_iam_role.rds_monitoring.arn

  # Deletion protection for production
  deletion_protection = var.environment == "prod" ? true : false
  skip_final_snapshot = var.environment != "prod"

  # Performance Insights
  performance_insights_enabled = true
  performance_insights_retention_period = var.environment == "prod" ? 7 : 7

  tags = {
    Name        = "${var.project_name}-${var.environment}-db"
    Environment = var.environment
  }
}

# Read Replica for Production (for read scaling)
resource "aws_db_instance" "read_replica" {
  count = var.environment == "prod" ? 2 : 0

  identifier = "${var.project_name}-${var.environment}-db-replica-${count.index + 1}"

  # Replica configuration
  replicate_source_db = aws_db_instance.main.id
  instance_class      = var.environment_config[var.environment].db_instance_class

  # Storage configuration
  storage_type      = "gp3"
  storage_encrypted = true

  # Network configuration
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false

  # Performance configuration
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # Performance Insights
  performance_insights_enabled = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-replica-${count.index + 1}"
    Environment = var.environment
    Type        = "ReadReplica"
  }
}

# IAM Role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-${var.environment}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-monitoring"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}