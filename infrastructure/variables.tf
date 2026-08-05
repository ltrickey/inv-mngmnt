variable "aws_region" {
  description = "Region for given AWS resources"
  type        = string
  default     = "us-east-1"
}

variable "iam_role_name" {
  description = "Name of the IAM role used as the execution/task role for all ECS Fargate services. Defaults to 'LabRole' (AWS Academy). The role must have permissions for DynamoDB, CloudWatch, etc."
  type        = string
  default     = "LabRole"
}

#TODO: Find out what this should be for production
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to reach the public ALBs"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict this in production
}

variable "environment" {
  description = "Environment name (e.g., test, prod)"
  type        = string
  default     = "test"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "product-catalogue"
}

variable "short_name" {
  description = "Short project name for resources with strict name length limits (e.g., Load Balancers)"
  type        = string
  default     = "pcat"
}

# ============================================================================
# API Gateway Variables
# ============================================================================

variable "api_quota_limit" {
  description = "Maximum number of requests per day per API key"
  type        = number
  default     = 10000
}

variable "api_rate_limit" {
  description = "Steady-state request rate limit (requests per second)"
  type        = number
  default     = 100
}

variable "api_burst_limit" {
  description = "Maximum concurrent requests (burst)"
  type        = number
  default     = 200
}

variable "log_retention_days" {
  description = "Number of days to retain API Gateway logs"
  type        = number
  default     = 7
}

