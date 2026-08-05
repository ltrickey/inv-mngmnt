data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "default" {
  id = data.aws_subnets.default.ids[0]
}

resource "aws_security_group" "inventory_api" {
  name        = "${local.name_prefix}-inventory-api-sg"
  description = "Security group for inventory API ECS Fargate tasks"
  vpc_id      = data.aws_vpc.default.id

  lifecycle {
    create_before_destroy = true
  }

  # Allow incoming traffic from customer ECS tasks on port 9000
  ingress {
    description     = "FastAPI from customer API ECS tasks"
    from_port       = 9000
    to_port         = 9000
    protocol        = "tcp"
    security_groups = [aws_security_group.customer_ecs.id]
  }

  # Allow incoming traffic from VPC for the internal NLB (API Gateway VPC Link,
  # and the employee BFF, both of which reach this service through that NLB)
  ingress {
    description = "FastAPI from internal NLB"
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-inventory-api-sg"
  })
}