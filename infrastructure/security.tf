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
  description = "Security group for inventory API EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  # Ensure EC2 instance is destroyed before security group
  # This prevents deletion timeout issues
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

  # Allow incoming traffic from VPC for API Gateway (via NLB)
  ingress {
    description = "FastAPI from API Gateway via VPC Link"
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  # Allow SSH access for management
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
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