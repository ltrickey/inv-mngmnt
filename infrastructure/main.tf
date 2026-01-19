# Configure the AWS Provider
# set env vars for:
# % export AWS_ACCESS_KEY_ID=""
# % export AWS_SECRET_ACCESS_KEY=""


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
