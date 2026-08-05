output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "name_prefix" {
  description = "Prefix used for resource names (e.g. DynamoDB tables: name_prefix-products)"
  value       = local.name_prefix
}

output "iam_role_name" {
  description = "IAM role used as the execution/task role for all ECS Fargate services"
  value       = local.iam_role_name
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