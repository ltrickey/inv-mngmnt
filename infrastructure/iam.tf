# Look up existing IAM role, used as both the execution role and task role
# for all three ECS Fargate services (customer API, employee BFF, inventory API).
# In AWS Academy, this is "LabRole" (pre-created with required permissions)
# In custom AWS accounts, specify your role name via variable
data "aws_iam_role" "ec2_role" {
  name = var.iam_role_name
}

locals {
  iam_role_name = data.aws_iam_role.ec2_role.name
}