/*
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

#TODO: Lynn not sure about this took this from Tim's example
#https://github.com/tim-spinney/cloud_project_manager/blob/52525410ee89a8cbf1c50eeb639dc6a198354c5b/infrastructure/variables.tf
 resource "aws_security_group" "product_catalogue" {
  name        = "${local.name_prefix}-product-catalogue-sg"
  description = "Security group for customer website EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 3000
    to_port     = 3000
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
    Name = "${local.name_prefix}-produxt-catalogue-sg"
  })
}
*/