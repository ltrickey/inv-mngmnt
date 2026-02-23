# Cognito User Pool for employee-facing internal website
resource "aws_cognito_user_pool" "employees" {
  name = "${local.name_prefix}-employees"

  # Employees are created by admins, not self-registered
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  # Allow sign-in with email or username
  username_attributes = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-employees"
  })
}

# App client for the React SPA (no client secret -- public client)
resource "aws_cognito_user_pool_client" "employee_site" {
  name         = "${local.name_prefix}-employee-site"
  user_pool_id = aws_cognito_user_pool.employees.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]

  prevent_user_existence_errors = "ENABLED"
}
