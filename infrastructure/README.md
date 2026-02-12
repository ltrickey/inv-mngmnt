# Infrastructure Documentation

This directory contains Terraform configuration for deploying the Product Catalogue application to AWS.

## Quick Start

```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

## Configuration

### Using AWS Academy / Learner Lab (Default)

The configuration is pre-configured for AWS Academy with sensible defaults:
- IAM Instance Profile: `LabInstanceProfile`
- EC2 Key Pair: `vockey`
- Region: `us-east-1`

No additional configuration needed - just run `terraform apply`!

### Using Custom AWS Account

Create a `terraform.tfvars` file to override defaults:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

Example `terraform.tfvars`:

```hcl
aws_region                = "us-west-2"
environment               = "prod"
project_name              = "my-product-catalogue"
iam_instance_profile_name = "MyCustomProfile"
ec2_key_pair              = "my-keypair"
allowed_cidr_blocks       = ["1.2.3.4/32"]  # Your IP only
```

### Creating a Custom Instance Profile

If you want Terraform to create the instance profile instead of using an existing one:

```hcl
# In terraform.tfvars
create_instance_profile = true
```

This will create a new instance profile named `{project_name}-{environment}-ec2-profile` using the existing `LabRole`.

## Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `aws_region` | AWS region to deploy resources | `us-east-1` | No |
| `environment` | Environment name (dev, test, prod) | `test` | No |
| `project_name` | Project name for resource naming | `product-catalogue` | No |
| `iam_role_name` | IAM role name (contains permissions) | `LabRole` | No |
| `iam_instance_profile_name` | IAM instance profile name (wrapper for role) | `LabInstanceProfile` | No |
| `create_instance_profile` | Create new instance profile vs use existing | `false` | No |
| `ec2_key_pair` | EC2 key pair name for SSH | `vockey` | No |
| `allowed_cidr_blocks` | CIDR blocks allowed to access EC2 | `["0.0.0.0/0"]` | No |

## Architecture

The infrastructure creates:

### Compute Resources
- **Product Catalogue EC2 Instance** (`t4g.micro`)
  - Runs Flask application serving React frontend
  - Port 8000: Web application (public)
  - Port 22: SSH access

- **Inventory API EC2 Instance** (`t4g.micro`)
  - Runs FastAPI inventory service
  - Port 9000: API (private, accessible only from Product Catalogue)
  - Port 22: SSH access

### Security Groups
- **product_catalogue-sg**: Allows inbound on ports 8000 (HTTP) and 22 (SSH)
- **inventory_api-sg**: Allows inbound on port 9000 from product_catalogue-sg only, and 22 (SSH)

### DynamoDB Tables
- `{name_prefix}-products`: Product catalog data
- `{name_prefix}-stores`: Store locations
- `{name_prefix}-products_by_store`: Per-store inventory
- `categories`: Product categories (fixed name)

### S3 Storage (Always created for AWS deployments)
- **S3 Bucket**: `{name_prefix}-product-images`
  - Stores product images
  - **Private bucket** - not publicly accessible
  - Images accessed via time-limited signed URLs (1-hour expiration)
  - Versioning enabled
  - CORS configured for web access
  - Automatically populated from `infrastructure/images/`
- **Local Development**: Images served from `infrastructure/images/` directory (no S3)

### IAM (Identity and Access Management)

**Understanding IAM Role vs Instance Profile:**

```
IAM Role                    Instance Profile              EC2 Instance
┌─────────────────┐        ┌──────────────────┐          ┌──────────────┐
│ LabRole         │   →    │ LabInstanceProfile│    →    │ EC2 Instance │
│                 │        │                  │          │              │
│ - DynamoDB      │        │ Contains:        │          │ Uses profile │
│ - CloudWatch    │        │   LabRole        │          │ to access    │
│ - S3 (optional) │        │                  │          │ AWS services │
└─────────────────┘        └──────────────────┘          └──────────────┘
  Permissions                  Wrapper                      Application
```

**Configuration Options:**
- **Role**: Configurable via `iam_role_name` variable (default: `LabRole`)
- **Instance Profile**: Configurable via `iam_instance_profile_name` (default: `LabInstanceProfile`)
- **Create Profile**: Set `create_instance_profile = true` to have Terraform create a new profile

## Network Architecture

```
Internet
    |
    +------------------+------------------+
    |                  |                  |
    v                  v                  v
[Users]      [S3 Product Images]  [Product Catalogue EC2] :8000
              (public read)              |
                                        | (private network)
                                        v
                             [Inventory API EC2] :9000 (private)
                                        |
                                        v
                                  [DynamoDB Tables]
```

### Security Notes

1. **Product Catalogue** is publicly accessible on port 8000
2. **Inventory API** is only accessible from Product Catalogue instance via private IP
3. Both instances have SSH access (port 22) - restrict `allowed_cidr_blocks` in production
4. All instances use VPC default subnet
5. Outbound traffic allowed for both instances (for updates, DynamoDB access)

## Outputs

After `terraform apply`, you'll get:

```bash
# View all outputs
terraform output

# Specific outputs
terraform output service_url              # Product catalogue URL
terraform output inventory_api_url        # Internal inventory API URL
terraform output ec2_instance_public_dns  # Product catalogue DNS
terraform output iam_instance_profile     # IAM profile being used
terraform output s3_bucket_url            # S3 bucket URL for images
```

## Deployment

The infrastructure automatically deploys the applications when created:

1. **Product Catalogue**: Packages React app + Flask, deploys to EC2
2. **Inventory API**: Packages FastAPI app, deploys to EC2
3. **DynamoDB**: Seeds tables with initial data

### Manual Deployment

To redeploy without recreating infrastructure:

```bash
# Deploy everything
../scripts/deploy_all.sh

# Or deploy individually
../scripts/deploy_remote.sh              # Product catalogue
../scripts/deploy_inventory_api_remote.sh  # Inventory API
```

## Troubleshooting

### IAM Issues

**Error: Role not found**
```
Error: error reading IAM Role (MyRole): NoSuchEntity
```
Solution: Ensure the role exists or update `iam_role_name` variable
```bash
aws iam list-roles | grep RoleName
```

**Error: Instance profile not found**
```
Error: error reading IAM Instance Profile (MyProfile): NoSuchEntity
```

**For AWS Academy:**
- Ensure you're using the correct names (default: `LabRole` and `LabInstanceProfile`)
- Check: `aws iam list-instance-profiles`

**For Custom AWS:**
- Verify the profile exists: `aws iam get-instance-profile --instance-profile-name MyProfile`
- Or set `create_instance_profile = true` in your `terraform.tfvars` to create one

**Understanding the relationship:**
- The **role** must exist (has the permissions)
- The **instance profile** wraps the role (allows EC2 to use it)
- If `create_instance_profile = true`, Terraform creates a new profile using your existing role
- If `create_instance_profile = false`, both role and profile must already exist

### SSH Key Not Found

Ensure your SSH key exists:
- AWS Academy: `~/.ssh/vockey.pem`
- Custom: `~/.ssh/{your-key-name}.pem`

Set correct permissions: `chmod 400 ~/.ssh/vockey.pem`

### DynamoDB Tables Empty

Run the seed script:
```bash
cd ..
./scripts/check_and_seed_db.sh
```

### Service Not Starting

SSH into the instance and check logs:
```bash
ssh -i ~/.ssh/vockey.pem ec2-user@{instance-ip}

# Check Flask service
sudo systemctl status product_catalogue_flask
sudo journalctl -u product_catalogue_flask -f

# Check Inventory API service
sudo systemctl status inventory_api
sudo journalctl -u inventory_api -f
```

## File Structure

```
infrastructure/
├── main.tf           # Provider, AMI, common locals
├── ec2.tf            # EC2 instance definitions
├── security.tf       # Security groups, VPC data sources
├── iam.tf            # IAM roles and instance profiles
├── dynamodb.tf       # DynamoDB table definitions
├── deploy.tf         # Deployment automation
├── outputs.tf        # Terraform outputs
├── variables.tf      # Input variables
├── terraform.tf      # Terraform/provider version constraints
└── README.md         # This file
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all EC2 instances, security groups, and DynamoDB tables. Data in DynamoDB will be lost.

## Image Hosting

### Two Deployment Modes

**1. Local Development**
- Images served from `infrastructure/images/` directory
- Flask serves images at `/images/` endpoint
- No S3 needed

**2. AWS Deployment (via Terraform)**
- Images automatically uploaded to S3 bucket
- S3 bucket URL configured in Flask environment
- Better performance and scalability

**Quick commands:**
```bash
# Upload images to S3 (after terraform apply)
./scripts/upload_images_to_s3.sh

# View S3 bucket name
terraform output s3_bucket_name

# Note: Images are private and accessible only via signed URLs from Flask
```

See [S3_CONFIGURATION.md](S3_CONFIGURATION.md) for details.

## Additional Resources

- [IAM Configuration Guide](IAM_CONFIGURATION.md)
- [S3 Configuration Guide](S3_CONFIGURATION.md)
- [AWS Academy Documentation](https://awsacademy.instructure.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Project Root README](../README.md)
