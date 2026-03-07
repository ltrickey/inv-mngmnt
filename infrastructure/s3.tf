# S3 bucket for hosting product images
# Images will be publicly accessible for the web application
# This is always created when deploying to AWS
# For local development, the Flask app serves images from infrastructure/images/

resource "aws_s3_bucket" "product_images" {
  bucket = "${local.name_prefix}-product-images-${local.account_id}"
  
  # Allow Terraform to destroy the bucket even if it contains objects
  # This will delete all objects and versions when running terraform destroy
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-product-images"
  })
}

# Enable versioning for the bucket (optional but recommended)
resource "aws_s3_bucket_versioning" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Allow public read access for product images (non-sensitive static assets)
resource "aws_s3_bucket_public_access_block" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Public-read policy so browsers can fetch images directly (no presigned URLs needed)
resource "aws_s3_bucket_policy" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  depends_on = [aws_s3_bucket_public_access_block.product_images]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadImages"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.product_images.arn}/*"
      },
      {
        Sid    = "AllowEC2UploadAccess"
        Effect = "Allow"
        Principal = {
          AWS = data.aws_iam_role.ec2_role.arn
        }
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.product_images.arn}",
          "${aws_s3_bucket.product_images.arn}/*"
        ]
      }
    ]
  })
}

# CORS configuration for web access
resource "aws_s3_bucket_cors_configuration" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]  # In production, restrict to your domain
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Lifecycle rule to manage old versions (optional)
resource "aws_s3_bucket_lifecycle_configuration" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# S3 bucket for storing generated report CSV files (private — accessed via presigned URLs)
resource "aws_s3_bucket" "reports" {
  bucket        = "${local.name_prefix}-reports-${local.account_id}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-reports"
  })
}

resource "aws_s3_bucket_public_access_block" "reports" {
  bucket = aws_s3_bucket.reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CORS needed for presigned URL downloads initiated by the browser
resource "aws_s3_bucket_cors_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}

locals {
  s3_bucket_name = aws_s3_bucket.product_images.id
  s3_bucket_url  = "https://${aws_s3_bucket.product_images.bucket}.s3.amazonaws.com"
  reports_bucket = aws_s3_bucket.reports.id
}
