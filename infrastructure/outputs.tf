output "ec2_instance_id" {
  description = "ID of the product catalogue EC2 instance"
  value       = aws_instance.product_catalogue.id
}

output "ec2_instance_public_ip" {
  description = "Public IP address of the product catalogue EC2 instance"
  value       = aws_instance.product_catalogue.public_ip
}

output "ec2_instance_public_dns" {
  description = "Public DNS name of the product catalogue EC2 instance"
  value       = aws_instance.product_catalogue.public_dns
}

output "inventory_api_instance_id" {
  description = "ID of the inventory API EC2 instance"
  value       = aws_instance.inventory_api.id
}

output "inventory_api_public_ip" {
  description = "Public IP address of the inventory API EC2 instance"
  value       = aws_instance.inventory_api.public_ip
}

output "inventory_api_public_dns" {
  description = "Public DNS name of the inventory API EC2 instance"
  value       = aws_instance.inventory_api.public_dns
}

output "inventory_api_private_ip" {
  description = "Private IP address of the inventory API EC2 instance (for internal VPC communication)"
  value       = aws_instance.inventory_api.private_ip
}

/* output "s3_bucket_name" {
  description = "Name of the S3 bucket for build artifacts"
  value       = aws_s3_bucket.build_artifacts.id
} */


output "service_url" {
  description = "URL to access the product catalogue via the flask app hosting react's index.html"
  value       = "http://${aws_instance.product_catalogue.public_dns}:8000"
}

output "inventory_api_url" {
  description = "Internal URL for the inventory API (accessible from product catalogue instance)"
  value       = "http://${aws_instance.inventory_api.private_ip}:9000"
}

output "inventory_api_health_url" {
  description = "Health check endpoint for inventory API"
  value       = "http://${aws_instance.inventory_api.private_ip}:9000/health"
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "ec2_key_pair" {
  description = "EC2 key pair name for SSH access"
  value       = var.ec2_key_pair
}

output "name_prefix" {
  description = "Prefix used for resource names (e.g. DynamoDB tables: name_prefix-products)"
  value       = local.name_prefix
}

output "iam_role_name" {
  description = "IAM role used by EC2 instances"
  value       = local.iam_role_name
}

output "iam_instance_profile" {
  description = "IAM instance profile used by EC2 instances"
  value       = local.instance_profile_name
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for product images (private - requires signed URLs)"
  value       = aws_s3_bucket.product_images.id
}

output "s3_bucket_region" {
  description = "AWS region of the S3 bucket"
  value       = var.aws_region
}