# Configure the AWS Provider
# Credentials can be set via:
# 1. Environment variables:
#    export AWS_ACCESS_KEY_ID=""
#    export AWS_SECRET_ACCESS_KEY=""
#    export AWS_SESSION_TOKEN=""  # Required for temporary credentials
# 2. AWS credentials file (~/.aws/credentials):
#    [default]
#    aws_access_key_id = YOUR_ACCESS_KEY
#    aws_secret_access_key = YOUR_SECRET_KEY
#    aws_session_token = YOUR_SESSION_TOKEN  # Required for temporary credentials
# 3. AWS CLI: aws configure

provider "aws" {
    region = var.aws_region
}

data "aws_ami" "amazon_linux" {
    most_recent = true
    owners      = ["amazon"]

    filter {
        name   = "image-id"
        values = ["ami-059afa9e3a9c7af0c"]
    }
}

data "aws_caller_identity" "current" {}

locals {
  name_prefix       = "${var.project_name}-${var.environment}"
  short_name_prefix = "${var.short_name}-${var.environment}"
  account_id        = data.aws_caller_identity.current.account_id
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}