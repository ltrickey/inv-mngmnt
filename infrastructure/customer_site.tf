# =============================================================================
# Customer Site Infrastructure
# - ECR repository for the Customer API Docker image
# - ECS Fargate cluster + service behind an ALB
# - S3 static website for the React frontend
# =============================================================================

# ---------------------------------------------------------------------------
# ECR Repository
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "customer_api" {
  name         = "${local.name_prefix}-customer-api"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-customer-api"
  })
}

# ---------------------------------------------------------------------------
# CloudWatch Log Group (ECS logs)
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "customer_api" {
  name              = "/ecs/${local.name_prefix}-customer-api"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Cluster
# ---------------------------------------------------------------------------

resource "aws_ecs_cluster" "customer" {
  name = "${local.name_prefix}-customer"

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Task Definition
# ---------------------------------------------------------------------------

resource "aws_ecs_task_definition" "customer_api" {
  family                   = "${local.name_prefix}-customer-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = data.aws_iam_role.ec2_role.arn
  task_role_arn            = data.aws_iam_role.ec2_role.arn

  container_definitions = jsonencode([
    {
      name      = "customer-api"
      image     = "${aws_ecr_repository.customer_api.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "USE_DYNAMODB", value = "1" },
        { name = "DYNAMODB_PRODUCTS_TABLE", value = aws_dynamodb_table.products.name },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "INVENTORY_API_BASE_URL", value = "http://${aws_instance.inventory_api.private_ip}:9000" },
        { name = "S3_BUCKET_URL", value = local.s3_bucket_url },
        { name = "S3_BUCKET_NAME", value = local.s3_bucket_name },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.customer_api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Security Groups
# ---------------------------------------------------------------------------

resource "aws_security_group" "customer_alb" {
  name        = "${local.name_prefix}-customer-alb-sg"
  description = "ALB for customer API"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-customer-alb-sg"
  })

  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "customer_ecs" {
  name        = "${local.name_prefix}-customer-ecs-sg"
  description = "ECS tasks for customer API"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "From ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.customer_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-customer-ecs-sg"
  })

  lifecycle { create_before_destroy = true }
}

# ---------------------------------------------------------------------------
# ALB
# ---------------------------------------------------------------------------

resource "aws_lb" "customer" {
  name               = "${local.short_name_prefix}-cust-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.customer_alb.id]
  subnets            = slice(data.aws_subnets.all_default.ids, 0, min(3, length(data.aws_subnets.all_default.ids)))

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-customer-alb"
  })
}

resource "aws_lb_target_group" "customer_api" {
  name        = "${local.short_name_prefix}-cust-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/debug"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = local.common_tags
}

resource "aws_lb_listener" "customer_http" {
  load_balancer_arn = aws_lb.customer.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.customer_api.arn
  }
}

# ---------------------------------------------------------------------------
# ECS Service
# ---------------------------------------------------------------------------

resource "aws_ecs_service" "customer_api" {
  name            = "${local.name_prefix}-customer-api"
  cluster         = aws_ecs_cluster.customer.id
  task_definition = aws_ecs_task_definition.customer_api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = slice(data.aws_subnets.all_default.ids, 0, min(3, length(data.aws_subnets.all_default.ids)))
    security_groups  = [aws_security_group.customer_ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.customer_api.arn
    container_name   = "customer-api"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.customer_http]

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# S3 Static Website for Customer React Frontend
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "customer_site" {
  bucket        = "${local.name_prefix}-customer-site-${local.account_id}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-customer-site"
  })
}

resource "aws_s3_bucket_website_configuration" "customer_site" {
  bucket = aws_s3_bucket.customer_site.id

  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

resource "aws_s3_bucket_public_access_block" "customer_site" {
  bucket = aws_s3_bucket.customer_site.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "customer_site" {
  bucket     = aws_s3_bucket.customer_site.id
  depends_on = [aws_s3_bucket_public_access_block.customer_site]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.customer_site.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_cors_configuration" "customer_site" {
  bucket = aws_s3_bucket.customer_site.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "customer_api_ecr_repository_url" {
  description = "ECR repository URL for the customer API Docker image"
  value       = aws_ecr_repository.customer_api.repository_url
}

output "customer_api_alb_url" {
  description = "URL of the customer API (ALB)"
  value       = "http://${aws_lb.customer.dns_name}"
}

output "customer_site_url" {
  description = "URL of the customer React site (S3)"
  value       = "http://${aws_s3_bucket_website_configuration.customer_site.website_endpoint}"
}

output "customer_site_bucket" {
  description = "S3 bucket name for the customer React site"
  value       = aws_s3_bucket.customer_site.id
}
