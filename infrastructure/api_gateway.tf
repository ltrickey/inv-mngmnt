# API Gateway for Inventory Service
# Exposes the inventory API endpoints with API key authentication

# ============================================================================
# REST API Gateway
# ============================================================================

resource "aws_api_gateway_rest_api" "inventory_api" {
  name        = "${local.name_prefix}-inventory-api"
  description = "Inventory Service API with API Key authentication"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "${local.name_prefix}-inventory-api"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# API Gateway Resources (URL paths)
# ============================================================================

# /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  parent_id   = aws_api_gateway_rest_api.inventory_api.root_resource_id
  path_part   = "api"
}

# /api/inventory
resource "aws_api_gateway_resource" "inventory" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "inventory"
}

# /api/inventory/{store_id}
resource "aws_api_gateway_resource" "store" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  parent_id   = aws_api_gateway_resource.inventory.id
  path_part   = "{store_id}"
}

# /api/inventory/{store_id}/{barcode}
resource "aws_api_gateway_resource" "item" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  parent_id   = aws_api_gateway_resource.store.id
  path_part   = "{barcode}"
}

# /api/inventory/{store_id}/{barcode}/price
resource "aws_api_gateway_resource" "price" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  parent_id   = aws_api_gateway_resource.item.id
  path_part   = "price"
}

# ============================================================================
# VPC Link for Private Integration with EC2
# ============================================================================

# Network Load Balancer for EC2 instance
resource "aws_lb" "inventory_api" {
  name               = "${local.short_name_prefix}-inv-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = [data.aws_subnet.default.id]

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-inventory-api-nlb"
  })
}

# Target group for the inventory API ECS Fargate service.
# target_type "ip" is required for awsvpc-mode Fargate tasks; the ECS service's
# load_balancer block (in fastapi_site.tf) registers/deregisters task IPs automatically.
resource "aws_lb_target_group" "inventory_api" {
  name        = "${local.short_name_prefix}-inv-tg"
  port        = 9000
  protocol    = "TCP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    protocol            = "TCP"
    port                = 9000
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-inventory-api-tg"
  })
}

# Listener for the NLB
resource "aws_lb_listener" "inventory_api" {
  load_balancer_arn = aws_lb.inventory_api.arn
  port              = 9000
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.inventory_api.arn
  }
}

# VPC Link to connect API Gateway to private NLB
resource "aws_api_gateway_vpc_link" "inventory_api" {
  name        = "${local.name_prefix}-inventory-api-vpc-link"
  description = "VPC Link for Inventory API"
  target_arns = [aws_lb.inventory_api.arn]

  tags = {
    Name        = "${local.name_prefix}-inventory-api-vpc-link"
    Environment = var.environment
  }
}

# ============================================================================
# API Methods - Stock Check (GET)
# ============================================================================

resource "aws_api_gateway_method" "check_stock" {
  rest_api_id      = aws_api_gateway_rest_api.inventory_api.id
  resource_id      = aws_api_gateway_resource.item.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true

  request_parameters = {
    "method.request.path.store_id"        = true
    "method.request.path.barcode"         = true
    "method.request.querystring.quantity" = true
  }
}

resource "aws_api_gateway_integration" "check_stock" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  resource_id = aws_api_gateway_resource.item.id
  http_method = aws_api_gateway_method.check_stock.http_method

  type                    = "HTTP_PROXY"
  integration_http_method = "GET"
  uri                     = "http://${aws_lb.inventory_api.dns_name}:9000/api/inventory/{store_id}/{barcode}"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.inventory_api.id

  request_parameters = {
    "integration.request.path.store_id"        = "method.request.path.store_id"
    "integration.request.path.barcode"         = "method.request.path.barcode"
    "integration.request.querystring.quantity" = "method.request.querystring.quantity"
  }
}

# ============================================================================
# API Methods - Get Price (GET)
# ============================================================================

resource "aws_api_gateway_method" "get_price" {
  rest_api_id      = aws_api_gateway_rest_api.inventory_api.id
  resource_id      = aws_api_gateway_resource.price.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true

  request_parameters = {
    "method.request.path.store_id" = true
    "method.request.path.barcode"  = true
  }
}

resource "aws_api_gateway_integration" "get_price" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  resource_id = aws_api_gateway_resource.price.id
  http_method = aws_api_gateway_method.get_price.http_method

  type                    = "HTTP_PROXY"
  integration_http_method = "GET"
  uri                     = "http://${aws_lb.inventory_api.dns_name}:9000/api/inventory/{store_id}/{barcode}/price"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.inventory_api.id

  request_parameters = {
    "integration.request.path.store_id" = "method.request.path.store_id"
    "integration.request.path.barcode"  = "method.request.path.barcode"
  }
}

# ============================================================================
# API Methods - Deduct Single (PATCH)
# ============================================================================

resource "aws_api_gateway_method" "deduct_single" {
  rest_api_id      = aws_api_gateway_rest_api.inventory_api.id
  resource_id      = aws_api_gateway_resource.item.id
  http_method      = "PATCH"
  authorization    = "NONE"
  api_key_required = true

  request_parameters = {
    "method.request.path.store_id" = true
    "method.request.path.barcode"  = true
  }
}

resource "aws_api_gateway_integration" "deduct_single" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  resource_id = aws_api_gateway_resource.item.id
  http_method = aws_api_gateway_method.deduct_single.http_method

  type                    = "HTTP_PROXY"
  integration_http_method = "PATCH"
  uri                     = "http://${aws_lb.inventory_api.dns_name}:9000/api/inventory/{store_id}/{barcode}"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.inventory_api.id

  request_parameters = {
    "integration.request.path.store_id" = "method.request.path.store_id"
    "integration.request.path.barcode"  = "method.request.path.barcode"
  }
}

# ============================================================================
# API Methods - Deduct Batch (PATCH)
# ============================================================================

resource "aws_api_gateway_method" "deduct_batch" {
  rest_api_id      = aws_api_gateway_rest_api.inventory_api.id
  resource_id      = aws_api_gateway_resource.store.id
  http_method      = "PATCH"
  authorization    = "NONE"
  api_key_required = true

  request_parameters = {
    "method.request.path.store_id" = true
  }
}

resource "aws_api_gateway_integration" "deduct_batch" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id
  resource_id = aws_api_gateway_resource.store.id
  http_method = aws_api_gateway_method.deduct_batch.http_method

  type                    = "HTTP_PROXY"
  integration_http_method = "PATCH"
  uri                     = "http://${aws_lb.inventory_api.dns_name}:9000/api/inventory/{store_id}"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.inventory_api.id

  request_parameters = {
    "integration.request.path.store_id" = "method.request.path.store_id"
  }
}

# ============================================================================
# CORS Configuration (OPTIONS methods)
# ============================================================================

# Enable CORS for all endpoints
module "cors_item" {
  source = "./modules/api_gateway_cors"

  api_id          = aws_api_gateway_rest_api.inventory_api.id
  api_resource_id = aws_api_gateway_resource.item.id

  depends_on = [aws_api_gateway_resource.item]
}

module "cors_price" {
  source = "./modules/api_gateway_cors"

  api_id          = aws_api_gateway_rest_api.inventory_api.id
  api_resource_id = aws_api_gateway_resource.price.id

  depends_on = [aws_api_gateway_resource.price]
}

module "cors_store" {
  source = "./modules/api_gateway_cors"

  api_id          = aws_api_gateway_rest_api.inventory_api.id
  api_resource_id = aws_api_gateway_resource.store.id

  depends_on = [aws_api_gateway_resource.store]
}

# ============================================================================
# API Key and Usage Plan
# ============================================================================

resource "aws_api_gateway_api_key" "inventory_api_key" {
  name        = "${local.name_prefix}-inventory-api-key"
  description = "API Key for Inventory Service"
  enabled     = true

  tags = {
    Name        = "${local.name_prefix}-inventory-api-key"
    Environment = var.environment
  }
}

resource "aws_api_gateway_usage_plan" "inventory_api_plan" {
  name        = "${local.name_prefix}-inventory-usage-plan"
  description = "Usage plan for Inventory API"

  api_stages {
    api_id = aws_api_gateway_rest_api.inventory_api.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }

  quota_settings {
    limit  = var.api_quota_limit
    period = "DAY"
  }

  throttle_settings {
    burst_limit = var.api_burst_limit
    rate_limit  = var.api_rate_limit
  }

  tags = {
    Name        = "${local.name_prefix}-inventory-usage-plan"
    Environment = var.environment
  }
}

resource "aws_api_gateway_usage_plan_key" "inventory_api_key" {
  key_id        = aws_api_gateway_api_key.inventory_api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.inventory_api_plan.id
}

# ============================================================================
# API Deployment
# ============================================================================

resource "aws_api_gateway_deployment" "inventory_api" {
  rest_api_id = aws_api_gateway_rest_api.inventory_api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.item.id,
      aws_api_gateway_resource.price.id,
      aws_api_gateway_resource.store.id,
      aws_api_gateway_method.check_stock.id,
      aws_api_gateway_method.get_price.id,
      aws_api_gateway_method.deduct_single.id,
      aws_api_gateway_method.deduct_batch.id,
      aws_api_gateway_integration.check_stock.id,
      aws_api_gateway_integration.get_price.id,
      aws_api_gateway_integration.deduct_single.id,
      aws_api_gateway_integration.deduct_batch.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_method.check_stock,
    aws_api_gateway_method.get_price,
    aws_api_gateway_method.deduct_single,
    aws_api_gateway_method.deduct_batch,
    aws_api_gateway_integration.check_stock,
    aws_api_gateway_integration.get_price,
    aws_api_gateway_integration.deduct_single,
    aws_api_gateway_integration.deduct_batch,
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.inventory_api.id
  rest_api_id   = aws_api_gateway_rest_api.inventory_api.id
  stage_name    = "prod"

  # Commented out - requires CloudWatch Logs role ARN set at account level
  # AWS Academy accounts don't have this configured
  # access_log_settings {
  #   destination_arn = aws_cloudwatch_log_group.api_gateway.arn
  #   format = jsonencode({
  #     requestId      = "$context.requestId"
  #     ip             = "$context.identity.sourceIp"
  #     caller         = "$context.identity.caller"
  #     user           = "$context.identity.user"
  #     requestTime    = "$context.requestTime"
  #     httpMethod     = "$context.httpMethod"
  #     resourcePath   = "$context.resourcePath"
  #     status         = "$context.status"
  #     protocol       = "$context.protocol"
  #     responseLength = "$context.responseLength"
  #     error          = "$context.error.message"
  #   })
  # }

  xray_tracing_enabled = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-inventory-api-prod"
  })
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${local.name_prefix}-inventory-api"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${local.name_prefix}-inventory-api-logs"
    Environment = var.environment
  }
}

# ============================================================================
# Outputs
# ============================================================================

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = aws_api_gateway_stage.prod.invoke_url
}

output "api_key_id" {
  description = "ID of the API key"
  value       = aws_api_gateway_api_key.inventory_api_key.id
}

output "api_key_value" {
  description = "Value of the API key (sensitive)"
  value       = aws_api_gateway_api_key.inventory_api_key.value
  sensitive   = true
}

output "api_gateway_rest_api_id" {
  description = "ID of the REST API"
  value       = aws_api_gateway_rest_api.inventory_api.id
}
