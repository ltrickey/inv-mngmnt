# Look up existing IAM role
# In AWS Academy, this is "LabRole" (pre-created with required permissions)
# In custom AWS accounts, specify your role name via variable
data "aws_iam_role" "ec2_role" {
  name = var.iam_role_name
}

# Option 1: Use existing instance profile (default for AWS Academy)
# The profile already exists and contains the role
data "aws_iam_instance_profile" "existing" {
  count = var.create_instance_profile ? 0 : 1
  name  = var.iam_instance_profile_name
}

# Option 2: Create a custom instance profile (for non-AWS Academy environments)
# This creates a new profile that wraps the existing role
resource "aws_iam_instance_profile" "custom" {
  count = var.create_instance_profile ? 1 : 0
  name  = "${local.name_prefix}-ec2-profile"
  role  = data.aws_iam_role.ec2_role.name

  tags = local.common_tags
}

# Local value to select the appropriate instance profile
locals {
  instance_profile_name = var.create_instance_profile ? aws_iam_instance_profile.custom[0].name : data.aws_iam_instance_profile.existing[0].name
  iam_role_name         = data.aws_iam_role.ec2_role.name
}