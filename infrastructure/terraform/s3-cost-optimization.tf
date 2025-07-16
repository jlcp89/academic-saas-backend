# S3 Bucket with Cost Optimization

# S3 Bucket for Static and Media Files
resource "aws_s3_bucket" "main" {
  bucket = var.s3_bucket_name != "" ? var.s3_bucket_name : "${var.project_name}-${var.environment}-${random_id.bucket_suffix.hex}"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-bucket"
    Type = "Static-Media"
  })
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = var.environment == "prod" ? "Enabled" : "Suspended"
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Server-side Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Lifecycle Configuration for Cost Optimization
resource "aws_s3_bucket_lifecycle_configuration" "main" {
  count = var.s3_lifecycle_enabled ? 1 : 0

  bucket = aws_s3_bucket.main.id

  # Static files lifecycle (CSS, JS, Images)
  rule {
    id     = "static_files_lifecycle"
    status = "Enabled"

    filter {
      prefix = "static/"
    }

    # Transition to IA after 30 days
    transition {
      days          = var.s3_transition_to_ia_days
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier after 90 days
    transition {
      days          = var.s3_transition_to_glacier_days
      storage_class = "GLACIER"
    }

    # Delete old versions after 1 year
    noncurrent_version_expiration {
      noncurrent_days = 365
    }

    # Delete incomplete multipart uploads after 7 days
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Media files lifecycle (User uploads)
  rule {
    id     = "media_files_lifecycle"
    status = "Enabled"

    filter {
      prefix = "media/"
    }

    # Transition to IA after 60 days
    transition {
      days          = 60
      storage_class = "STANDARD_IA"
    }

    # Transition to Glacier after 180 days
    transition {
      days          = 180
      storage_class = "GLACIER"
    }

    # Optionally delete after specified days (0 = never delete)
    dynamic "expiration" {
      for_each = var.s3_expiration_days > 0 ? [1] : []
      content {
        days = var.s3_expiration_days
      }
    }

    # Delete old versions after 2 years
    noncurrent_version_expiration {
      noncurrent_days = 730
    }
  }

  # Logs lifecycle (Temporary files, logs)
  rule {
    id     = "logs_lifecycle"
    status = "Enabled"

    filter {
      prefix = "logs/"
    }

    # Move to IA after 30 days (minimum required)
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 60 days
    transition {
      days          = 60
      storage_class = "GLACIER"
    }

    # Delete after 90 days
    expiration {
      days = 90
    }
  }

  # Temporary files cleanup
  rule {
    id     = "temp_files_cleanup"
    status = "Enabled"

    filter {
      prefix = "temp/"
    }

    # Delete temporary files after 1 day
    expiration {
      days = 1
    }
  }

  depends_on = [aws_s3_bucket_versioning.main]
}

# S3 Bucket Policy for CloudFront and Application Access
resource "aws_s3_bucket_policy" "main" {
  bucket = aws_s3_bucket.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.main.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.main.arn}/*"
      },
      {
        Sid    = "AllowApplicationAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.ec2.arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.main.arn}/*"
      },
      {
        Sid    = "DenyUnSecureCommunications"
        Effect = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# CloudFront Distribution for Global CDN and Cost Optimization
resource "aws_cloudfront_origin_access_identity" "main" {
  comment = "${var.project_name}-${var.environment} OAI"
}

resource "aws_cloudfront_distribution" "main" {
  origin {
    domain_name = aws_s3_bucket.main.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.main.bucket}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main.cloudfront_access_identity_path
    }
  }

  enabled         = true
  is_ipv6_enabled = true
  comment         = "${var.project_name} ${var.environment} CDN"
  default_root_object = "index.html"

  # Cost optimization: Use only North America and Europe
  price_class = var.environment == "prod" ? "PriceClass_100" : "PriceClass_100"

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.main.bucket}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600    # 1 hour
    max_ttl                = 86400   # 24 hours
  }

  # Cache behavior for static files (longer TTL)
  ordered_cache_behavior {
    path_pattern     = "/static/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "S3-${aws_s3_bucket.main.bucket}"

    forwarded_values {
      query_string = false
      headers      = ["Origin"]
      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 31536000  # 1 year
    max_ttl                = 31536000  # 1 year
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
  }

  # Cache behavior for media files
  ordered_cache_behavior {
    path_pattern     = "/media/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "S3-${aws_s3_bucket.main.bucket}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 86400    # 24 hours
    max_ttl                = 31536000 # 1 year
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-cdn"
    Type = "CDN"
  })
}

# S3 Analytics for Cost Optimization Insights
resource "aws_s3_bucket_analytics_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  name   = "cost-optimization-analytics"

  filter {
    prefix = "media/"
  }
}

# S3 Intelligent Tiering for Automatic Cost Optimization
resource "aws_s3_bucket_intelligent_tiering_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  name   = "intelligent-tiering"

  # Apply to all objects with "archive/" prefix
  filter {
    prefix = "archive/"
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}

# CloudWatch Metrics for S3 Cost Monitoring
resource "aws_cloudwatch_metric_alarm" "s3_storage_cost" {
  alarm_name          = "${var.project_name}-${var.environment}-s3-storage-cost"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # Daily
  statistic           = "Average"
  threshold           = "10737418240"  # 10 GB in bytes
  alarm_description   = "S3 bucket size exceeded 10GB"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    BucketName  = aws_s3_bucket.main.bucket
    StorageType = "StandardStorage"
  }

  tags = local.common_tags
}

# S3 Request Metrics for Cost Analysis
resource "aws_s3_bucket_request_payment_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  payer  = "BucketOwner"
}

# Output S3 information - moved to outputs.tf to avoid duplication
# All outputs are consolidated in outputs.tf