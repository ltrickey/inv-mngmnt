# =============================================================================
# Employee Internal Site Infrastructure
# - ECR repository for the BFF Docker image
# - ECS Fargate cluster + service behind an ALB
# - S3 static website for the React frontend
# =============================================================================

# Need at least 2 subnets in different AZs for the ALB
data "aws_subnets" "all_default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ---------------------------------------------------------------------------
# ECR Repository
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "employee_bff" {
  name         = "${local.name_prefix}-employee-bff"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-employee-bff"
  })
}

# ---------------------------------------------------------------------------
# CloudWatch Log Group (ECS logs)
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "employee_bff" {
  name              = "/ecs/${local.name_prefix}-employee-bff"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Cluster
# ---------------------------------------------------------------------------

resource "aws_ecs_cluster" "employee" {
  name = "${local.name_prefix}-employee"

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Task Definition
# ---------------------------------------------------------------------------

resource "aws_ecs_task_definition" "employee_bff" {
  family                   = "${local.name_prefix}-employee-bff"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = data.aws_iam_role.ec2_role.arn
  task_role_arn            = data.aws_iam_role.ec2_role.arn

  container_definitions = jsonencode([
    {
      name      = "employee-bff"
      image     = "${aws_ecr_repository.employee_bff.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 5001
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "COGNITO_USER_POOL_ID", value = aws_cognito_user_pool.employees.id },
        { name = "COGNITO_APP_CLIENT_ID", value = aws_cognito_user_pool_client.employee_site.id },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "PRODUCT_CATALOGUE_API_URL", value = "http://${aws_instance.product_catalogue.private_ip}:8000" },
        { name = "INVENTORY_API_URL", value = "http://${aws_instance.inventory_api.private_ip}:9000" },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.employee_bff.name
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

resource "aws_security_group" "employee_alb" {
  name        = "${local.name_prefix}-employee-alb-sg"
  description = "ALB for employee BFF"
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
    Name = "${local.name_prefix}-employee-alb-sg"
  })

  lifecycle { create_before_destroy = true }
}

resource "aws_security_group" "employee_ecs" {
  name        = "${local.name_prefix}-employee-ecs-sg"
  description = "ECS tasks for employee BFF"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "From ALB"
    from_port       = 5001
    to_port         = 5001
    protocol        = "tcp"
    security_groups = [aws_security_group.employee_alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-employee-ecs-sg"
  })

  lifecycle { create_before_destroy = true }
}

# ---------------------------------------------------------------------------
# ALB
# ---------------------------------------------------------------------------

resource "aws_lb" "employee" {
  name               = "${local.short_name_prefix}-emp-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.employee_alb.id]
  subnets            = slice(data.aws_subnets.all_default.ids, 0, min(3, length(data.aws_subnets.all_default.ids)))

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-employee-alb"
  })
}

resource "aws_lb_target_group" "employee_bff" {
  name        = "${local.short_name_prefix}-emp-bff-tg"
  port        = 5001
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/health"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
    matcher             = "200"
  }

  tags = local.common_tags
}

resource "aws_lb_listener" "employee_http" {
  load_balancer_arn = aws_lb.employee.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.employee_bff.arn
  }
}

# ---------------------------------------------------------------------------
# ECS Service
# ---------------------------------------------------------------------------

resource "aws_ecs_service" "employee_bff" {
  name            = "${local.name_prefix}-employee-bff"
  cluster         = aws_ecs_cluster.employee.id
  task_definition = aws_ecs_task_definition.employee_bff.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = slice(data.aws_subnets.all_default.ids, 0, min(3, length(data.aws_subnets.all_default.ids)))
    security_groups  = [aws_security_group.employee_ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.employee_bff.arn
    container_name   = "employee-bff"
    container_port   = 5001
  }

  depends_on = [aws_lb_listener.employee_http]

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Allow ECS tasks to reach the inventory API and product catalogue
# ---------------------------------------------------------------------------

resource "aws_security_group_rule" "inventory_api_from_ecs" {
  type                     = "ingress"
  from_port                = 9000
  to_port                  = 9000
  protocol                 = "tcp"
  security_group_id        = aws_security_group.inventory_api.id
  source_security_group_id = aws_security_group.employee_ecs.id
  description              = "Inventory API from employee BFF ECS tasks"
}

resource "aws_security_group_rule" "product_catalogue_from_ecs" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = aws_security_group.product_catalogue.id
  source_security_group_id = aws_security_group.employee_ecs.id
  description              = "Product catalogue from employee BFF ECS tasks"
}

# ---------------------------------------------------------------------------
# S3 Static Website for Employee React Frontend
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "employee_site" {
  bucket        = "${local.name_prefix}-employee-site-${local.account_id}"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-employee-site"
  })
}

resource "aws_s3_bucket_website_configuration" "employee_site" {
  bucket = aws_s3_bucket.employee_site.id

  index_document { suffix = "index.html" }
  error_document { key = "index.html" }
}

resource "aws_s3_bucket_public_access_block" "employee_site" {
  bucket = aws_s3_bucket.employee_site.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "employee_site" {
  bucket     = aws_s3_bucket.employee_site.id
  depends_on = [aws_s3_bucket_public_access_block.employee_site]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.employee_site.arn}/*"
      }
    ]
  })
}

resource "aws_s3_bucket_cors_configuration" "employee_site" {
  bucket = aws_s3_bucket.employee_site.id

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

output "ecr_repository_url" {
  description = "ECR repository URL for the employee BFF Docker image"
  value       = aws_ecr_repository.employee_bff.repository_url
}

output "employee_bff_alb_url" {
  description = "URL of the employee BFF (ALB)"
  value       = "http://${aws_lb.employee.dns_name}"
}

output "employee_site_url" {
  description = "URL of the employee React site (S3)"
  value       = "http://${aws_s3_bucket_website_configuration.employee_site.website_endpoint}"
}

output "employee_site_bucket" {
  description = "S3 bucket name for the employee React site"
  value       = aws_s3_bucket.employee_site.id
}
