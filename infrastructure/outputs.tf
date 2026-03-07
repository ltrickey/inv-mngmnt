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

# Cognito outputs for employee site
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID for the employee site"
  value       = aws_cognito_user_pool.employees.id
}

output "cognito_app_client_id" {
  description = "Cognito App Client ID for the employee site SPA"
  value       = aws_cognito_user_pool_client.employee_site.id
}

output "report_lambda_arn" {
  description = "ARN of the report generator Lambda function"
  value       = aws_lambda_function.report_generator.arn
}

output "report_schedule_group_name" {
  description = "EventBridge Scheduler group name for report schedules"
  value       = aws_scheduler_schedule_group.reports.name
}

output "reports_bucket_name" {
  description = "S3 bucket name for generated report CSV files"
  value       = aws_s3_bucket.reports.id
}