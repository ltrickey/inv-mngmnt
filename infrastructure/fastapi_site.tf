# =============================================================================
# Inventory API (FastAPI) Infrastructure
# - ECR repository for the FastAPI Docker image
# - ECS Fargate cluster + service
# - Registers into the internal NLB defined in api_gateway.tf, which is the
#   single path into this service for both internal callers (customer API,
#   employee BFF) and the external vendor API Gateway route.
# =============================================================================

# ---------------------------------------------------------------------------
# ECR Repository
# ---------------------------------------------------------------------------

resource "aws_ecr_repository" "inventory_api" {
  name         = "${local.name_prefix}-inventory-api"
  force_delete = true

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-inventory-api"
  })
}

# ---------------------------------------------------------------------------
# CloudWatch Log Group (ECS logs)
# ---------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "inventory_api" {
  name              = "/ecs/${local.name_prefix}-inventory-api"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Cluster
# ---------------------------------------------------------------------------

resource "aws_ecs_cluster" "inventory_api" {
  name = "${local.name_prefix}-inventory-api"

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Task Definition
# ---------------------------------------------------------------------------

resource "aws_ecs_task_definition" "inventory_api" {
  family                   = "${local.name_prefix}-inventory-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = data.aws_iam_role.ec2_role.arn
  task_role_arn            = data.aws_iam_role.ec2_role.arn

  container_definitions = jsonencode([
    {
      name      = "inventory-api"
      image     = "${aws_ecr_repository.inventory_api.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 9000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "USE_DYNAMODB", value = "1" },
        { name = "DYNAMODB_PRODUCTS_TABLE", value = aws_dynamodb_table.products.name },
        { name = "AWS_REGION", value = var.aws_region },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.inventory_api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# ECS Service — registers directly into the NLB target group from api_gateway.tf
# ---------------------------------------------------------------------------

resource "aws_ecs_service" "inventory_api" {
  name            = "${local.name_prefix}-inventory-api"
  cluster         = aws_ecs_cluster.inventory_api.id
  task_definition = aws_ecs_task_definition.inventory_api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = slice(data.aws_subnets.all_default.ids, 0, min(3, length(data.aws_subnets.all_default.ids)))
    security_groups  = [aws_security_group.inventory_api.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.inventory_api.arn
    container_name   = "inventory-api"
    container_port   = 9000
  }

  depends_on = [aws_lb_listener.inventory_api]

  tags = local.common_tags
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "inventory_api_ecr_repository_url" {
  description = "ECR repository URL for the inventory API Docker image"
  value       = aws_ecr_repository.inventory_api.repository_url
}

output "inventory_api_url" {
  description = "Internal URL for the inventory API (via NLB, VPC-only)"
  value       = "http://${aws_lb.inventory_api.dns_name}:9000"
}

output "inventory_api_health_url" {
  description = "Health check endpoint for the inventory API"
  value       = "http://${aws_lb.inventory_api.dns_name}:9000/health"
}
