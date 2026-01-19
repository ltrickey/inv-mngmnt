# Use existing IAM role "LabRole"
data "aws_iam_role" "LabRole" {
  name = "LabRole"
}

# IAM instance profile for EC2 (using existing LabRole)
# Note: The instance profile name may differ from the role name
# Update iam_instance_profile_name variable if your instance profile has a different name
data "aws_iam_instance_profile" "LabInstanceProfile" {
  name = var.iam_instance_profile_name
}