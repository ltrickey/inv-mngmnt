# IAM Configuration Guide

## Understanding IAM Role vs Instance Profile

### The Basics

**IAM Role** = A set of permissions (what can be done)
- Contains policies like "allow DynamoDB read/write"
- Example: `LabRole` with policies for DynamoDB, CloudWatch, S3

**IAM Instance Profile** = A container/wrapper for a role
- Allows EC2 instances to "wear" the role
- One profile contains exactly one role
- Example: `LabInstanceProfile` contains `LabRole`

### The Relationship

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS IAM System                           │
│                                                                 │
│  ┌─────────────────┐         ┌──────────────────────┐         │
│  │  IAM Role       │         │  Instance Profile    │         │
│  │  "LabRole"      │         │  "LabInstanceProfile"│         │
│  │                 │         │                      │         │
│  │  Policies:      │  ◀──────│  Contains: LabRole   │         │
│  │  - DynamoDB RW  │         │                      │         │
│  │  - CloudWatch   │         └──────────────────────┘         │
│  │  - S3 Access    │                   │                       │
│  └─────────────────┘                   │                       │
│                                        │                       │
└────────────────────────────────────────┼───────────────────────┘
                                         │
                                         │ EC2 uses profile
                                         │ to assume role
                                         ▼
                              ┌──────────────────┐
                              │  EC2 Instance    │
                              │                  │
                              │  Now has access  │
                              │  to DynamoDB,    │
                              │  CloudWatch, S3  │
                              └──────────────────┘
```

## Common Configuration Scenarios

### Scenario 1: AWS Academy / Learner Lab (Default)

**What exists:**
- Pre-created role: `LabRole`
- Pre-created profile: `LabInstanceProfile`
- Both have all needed permissions

**Your configuration:**
```hcl
# terraform.tfvars (or just use defaults)
iam_role_name = "LabRole"                    # optional, this is default
iam_instance_profile_name = "LabInstanceProfile"  # optional, this is default
create_instance_profile = false               # optional, this is default
```

**What Terraform does:**
- Looks up existing `LabRole` ✓
- Looks up existing `LabInstanceProfile` ✓
- Uses them as-is ✓

### Scenario 2: Custom AWS Account with Existing Role + Profile

**What exists:**
- Your custom role: `MyCompanyEC2Role`
- Your custom profile: `MyCompanyEC2Profile`

**Your configuration:**
```hcl
# terraform.tfvars
iam_role_name = "MyCompanyEC2Role"
iam_instance_profile_name = "MyCompanyEC2Profile"
create_instance_profile = false
```

**What Terraform does:**
- Looks up existing `MyCompanyEC2Role` ✓
- Looks up existing `MyCompanyEC2Profile` ✓
- Uses them as-is ✓

### Scenario 3: Custom AWS Account - Create Profile from Existing Role

**What exists:**
- Your role: `MyCompanyEC2Role` (with DynamoDB, CloudWatch policies)
- No profile yet

**Your configuration:**
```hcl
# terraform.tfvars
iam_role_name = "MyCompanyEC2Role"
create_instance_profile = true
# iam_instance_profile_name not needed - Terraform will create one
```

**What Terraform does:**
- Looks up existing `MyCompanyEC2Role` ✓
- Creates new profile: `product-catalogue-test-ec2-profile` ✓
- Profile wraps your existing role ✓
- Deletes profile when you run `terraform destroy` (role stays) ✓

### Scenario 4: Multiple Environments with Same Role

**What exists:**
- One role: `ProductionEC2Role`
- Multiple profiles: `ProductionEC2Profile`, `StagingEC2Profile`, `DevEC2Profile`

**Your configuration:**
```hcl
# production.tfvars
environment = "prod"
iam_role_name = "ProductionEC2Role"
iam_instance_profile_name = "ProductionEC2Profile"

# staging.tfvars
environment = "staging"
iam_role_name = "ProductionEC2Role"              # same role
iam_instance_profile_name = "StagingEC2Profile" # different profile
```

**What Terraform does:**
- All environments use the same role (permissions)
- Each environment uses its own profile
- Allows you to track which instances belong to which environment

## Required Permissions

The IAM role (e.g., `LabRole`) must have these permissions for the application to work:

### DynamoDB
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:BatchWriteItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/product-catalogue-*",
    "arn:aws:dynamodb:*:*:table/categories"
  ]
}
```

### CloudWatch (for logging)
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:*:*:*"
}
```

### Optional: S3 (if using S3 for images)
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject"
  ],
  "Resource": "arn:aws:s3:::your-bucket/*"
}
```

## Checking Your IAM Configuration

### List available roles
```bash
aws iam list-roles --query 'Roles[*].[RoleName]' --output table
```

### Check if a specific role exists
```bash
aws iam get-role --role-name LabRole
```

### List available instance profiles
```bash
aws iam list-instance-profiles --query 'InstanceProfiles[*].[InstanceProfileName,Roles[0].RoleName]' --output table
```

### Check if a specific profile exists
```bash
aws iam get-instance-profile --instance-profile-name LabInstanceProfile
```

### See what role is in a profile
```bash
aws iam get-instance-profile --instance-profile-name LabInstanceProfile \
  --query 'InstanceProfile.Roles[0].RoleName' --output text
```

## Troubleshooting

### Error: "NoSuchEntity: The role with name X cannot be found"
**Problem:** The IAM role doesn't exist

**Solution:**
1. Check the role name: `aws iam list-roles | grep RoleName`
2. Update your `terraform.tfvars`:
   ```hcl
   iam_role_name = "CorrectRoleName"
   ```

### Error: "NoSuchEntity: Instance Profile X cannot be found"
**Problem:** The instance profile doesn't exist

**Solution Option 1 - Use existing profile:**
1. Find existing profiles: `aws iam list-instance-profiles`
2. Update your `terraform.tfvars`:
   ```hcl
   iam_instance_profile_name = "CorrectProfileName"
   ```

**Solution Option 2 - Create new profile:**
```hcl
create_instance_profile = true
```

### Error: "Cannot exceed quota for InstanceProfiles"
**Problem:** You've hit the AWS limit for instance profiles

**Solution:**
1. List all profiles: `aws iam list-instance-profiles`
2. Delete unused ones: `aws iam delete-instance-profile --instance-profile-name UnusedProfile`
3. Or use an existing profile: `create_instance_profile = false`

## Best Practices

1. **Use Existing Resources in AWS Academy**
   - Don't create custom profiles - use the provided `LabInstanceProfile`
   - AWS Academy has limited permissions

2. **Separate Roles by Environment in Production**
   - Dev: `ProductCatalogue-Dev-Role`
   - Prod: `ProductCatalogue-Prod-Role`
   - Different permissions (dev might have more debugging access)

3. **Use Least Privilege**
   - Only grant permissions that are actually needed
   - Don't use `"Resource": "*"` unless necessary

4. **Version Control Your IAM Config**
   - Keep `terraform.tfvars` in version control (remove secrets first!)
   - Document why you chose specific roles/profiles

5. **Test Changes in Dev First**
   - Never change IAM configuration directly in production
   - Test with a separate environment variable first

## Quick Reference

| You Have | You Want | Configuration |
|----------|----------|---------------|
| AWS Academy | Use defaults | No config needed! |
| Custom role + profile | Use them | Set both variable names |
| Custom role only | Create profile | Set role name + `create_instance_profile = true` |
| Different envs | Separate profiles | Use different profile names per env |

## Example Terraform Commands

```bash
# Check what role/profile will be used without applying
terraform plan -var="iam_role_name=MyRole"

# Apply with custom role
terraform apply -var="iam_role_name=MyRole" -var="create_instance_profile=true"

# See current IAM configuration
terraform output iam_role_name
terraform output iam_instance_profile
```
