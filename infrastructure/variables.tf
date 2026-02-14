variable "aws_region" {
  description = "Region for given AWS resources"
  type        = string
  default     = "us-east-1"
}

variable "iam_role_name" {
  description = "Name of the IAM role to use for EC2 instances. Defaults to 'LabRole' (AWS Academy). The role must have permissions for DynamoDB, CloudWatch, etc."
  type        = string
  default     = "LabRole"
}

variable "iam_instance_profile_name" {
  description = "Name of the IAM instance profile to use for EC2 instances. Defaults to 'LabInstanceProfile' (AWS Academy default). Override via -var or terraform.tfvars"
  type        = string
  default     = "LabInstanceProfile"
}

variable "create_instance_profile" {
  description = "Whether to create a new instance profile or use an existing one. Set to true for custom AWS accounts if you want Terraform to create the profile."
  type        = bool
  default     = false
}

variable "ec2_key_pair" {
  description = "Name of the key pair to use for SSH access to EC2 instances"
  type        = string
  default     = "vockey"
}

#TODO: Find out what this should be for production
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the EC2 instance"
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

