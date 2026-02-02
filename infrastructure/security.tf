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

resource "aws_security_group" "product_catalogue" {
  name        = "${local.name_prefix}-product-catalogue-sg"
  description = "Security group for product catalogue customer website EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  # Ensure EC2 instance is destroyed before security group
  # This prevents deletion timeout issues
  lifecycle {
    create_before_destroy = true
  }

  # Flask serves both React app (static files) and API endpoints
  # React app is built and served as static files by Flask
  ingress {
    description = "Flask App (React + API)"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

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
    Name = "${local.name_prefix}-product-catalogue-sg"
  })
}