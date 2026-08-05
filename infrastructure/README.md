# Infrastructure Documentation

This directory contains Terraform configuration for deploying the Product Catalogue / Inventory application to AWS. See [../SystemDesign.md](../SystemDesign.md) for the application-level architecture.

## Quick Start

```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

`terraform apply` provisions the infrastructure **and** builds/pushes Docker images and deploys the three services (via `terraform_data` provisioners in `deploy.tf`), so a single `apply` gets you a working stack.

## Configuration

### Using AWS Academy / Learner Lab (Default)

The configuration is pre-configured for AWS Academy with sensible defaults:
- IAM Role: `LabRole` (used as the ECS execution/task role for all three services)
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
aws_region          = "us-west-2"
environment         = "prod"
project_name        = "my-product-catalogue"
iam_role_name       = "MyECSExecutionRole"
allowed_cidr_blocks = ["1.2.3.4/32"]  # Your IP only
```

The IAM role must allow ECR image pulls, CloudWatch Logs writes, and DynamoDB access.

## Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `aws_region` | AWS region to deploy resources | `us-east-1` | No |
| `environment` | Environment name (dev, test, prod) | `test` | No |
| `project_name` | Project name for resource naming | `product-catalogue` | No |
| `iam_role_name` | IAM role used as the ECS execution/task role for all services | `LabRole` | No |
| `allowed_cidr_blocks` | CIDR blocks allowed to reach the public ALBs | `["0.0.0.0/0"]` | No |

## Architecture

All three backend services run as **ECS Fargate** tasks (containerized, no bare EC2 instances). Both React SPAs are static S3 sites.

### Compute Resources
- **Customer API** (`customer_site.tf`) — Flask, ECS Fargate behind a public ALB, port 8000. Talks directly to DynamoDB.
- **Employee BFF** (`employee_site.tf`) — Flask, ECS Fargate behind a public ALB, port 5001. Cognito-JWT-gated; proxies to the Customer API and the Inventory API; owns report scheduling.
- **Inventory API** (`fastapi_site.tf`) — FastAPI, ECS Fargate, port 9000. Not behind a public ALB — reachable only through the internal NLB defined in `api_gateway.tf`, which both internal callers (via VPC) and the external vendor-facing API Gateway route use.

### Security Groups
- **customer-alb-sg / customer-ecs-sg**: public ALB → ECS tasks on 8000
- **employee-alb-sg / employee-ecs-sg**: public ALB → ECS tasks on 5001
- **inventory-api-sg**: allows 9000 from `customer-ecs-sg` and from anywhere inside the VPC (covers the internal NLB, used by both the employee BFF and API Gateway's VPC Link)

### DynamoDB Tables
- `{name_prefix}-products`: Product catalog data
- `{name_prefix}-stores`: Store locations
- `{name_prefix}-products_by_store`: Per-store inventory + pricing
- `{name_prefix}-sales_events`: POS transaction log (streams enabled)
- `{name_prefix}-report_schedules` / `{name_prefix}-report_results`: scheduled reporting
- `categories`: Product categories (fixed name)

### S3 Storage
- **Product images bucket** — private, signed-URL access, versioned, populated from `infrastructure/images/`
- **Reports bucket** — CSV report output, written by the report Lambda, downloaded via presigned URL from the employee BFF
- **Customer / Employee site buckets** — public static website hosting for the two React SPAs

### Scheduled Reporting
- `lambda.tf` provisions the `report_lambda` function and an EventBridge Scheduler group
- The employee BFF creates a per-user EventBridge Scheduler schedule when a report is configured; the schedule invokes the Lambda on its cadence

### Cognito
- `cognito.tf` provisions one user pool + app client for the employee site only (admin-created users, no self-signup)

### IAM

All three ECS task definitions share a single execution/task role (`iam.tf`, `data.aws_iam_role.ec2_role`), configurable via `iam_role_name`. On AWS Academy this is the pre-created `LabRole`. No instance profiles are needed — Fargate tasks use the execution/task role directly.

## Network Architecture

```
Internet
    |
    +------------------+------------------+------------------+
    |                  |                  |                  |
    v                  v                  v                  v
[Customers]      [Employees]      [Vendor / POS]      [S3: images, SPAs]
    |                  |                  |
    v                  v                  v
[Customer ALB]   [Employee ALB]   [API Gateway :api-key]
    |                  |                  |
    v                  v                  v
[Customer API    [Employee BFF    [VPC Link -> internal NLB]
 ECS Fargate] <--- ECS Fargate]          |
    |                  |                  v
    |                  +---------> [Inventory API ECS Fargate]
    v                                     |
              [DynamoDB Tables] <---------+
```

### Security Notes

1. **Customer API** and **Employee BFF** are publicly accessible via their ALBs (port 80)
2. **Inventory API** has no public ALB — only reachable via the internal NLB, from inside the VPC or through API Gateway
3. All ECS tasks run in the default VPC's default subnets with `assign_public_ip = true` (so Fargate can pull images without a NAT Gateway); inbound access is still restricted by security groups
4. Restrict `allowed_cidr_blocks` in production

## Outputs

After `terraform apply`, you'll get:

```bash
# View all outputs
terraform output

# Specific outputs
terraform output customer_site_url        # Customer SPA URL (S3)
terraform output employee_site_url        # Employee SPA URL (S3)
terraform output inventory_api_url        # Internal inventory API URL (NLB, VPC-only)
terraform output api_gateway_url          # Vendor-facing API Gateway URL
terraform output s3_bucket_name           # S3 bucket for product images
```

## Deployment

`terraform apply` automatically deploys all three services on first run (via `terraform_data` provisioners in `deploy.tf`):

1. **Inventory API**: builds/pushes the Docker image to ECR, deploys to ECS Fargate
2. **DynamoDB**: seeds tables with initial data
3. **Customer site**: builds/pushes the Docker image, builds the React SPA, uploads to S3, deploys to ECS Fargate
4. **Employee site**: builds/pushes the Docker image, builds the React SPA, uploads to S3, deploys to ECS Fargate

### Manual Redeploy

To redeploy a single service without recreating infrastructure:

```bash
cd infrastructure

ECR_REPOSITORY_URL=$(terraform output -raw inventory_api_ecr_repository_url) \
AWS_REGION=$(terraform output -raw aws_region) \
ECS_CLUSTER=$(terraform output -raw name_prefix)-inventory-api \
ECS_SERVICE=$(terraform output -raw name_prefix)-inventory-api \
../scripts/deploy_inventory_api.sh

# See scripts/deploy_customer_site.sh and scripts/deploy_employee_site.sh
# for the equivalent commands for those two services (they also need the
# ALB URL and, for the employee site, Cognito env vars — see deploy.tf).
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

### DynamoDB Tables Empty

Run the seed script:
```bash
cd ..
./scripts/check_and_seed_db.sh
```

### Service Not Starting

Check ECS service status and CloudWatch logs — no SSH needed, everything runs as a container:
```bash
./scripts/check_status.sh   # Inventory API ECS service status + recent events

# Or directly:
aws ecs describe-services --cluster {name_prefix}-inventory-api --services {name_prefix}-inventory-api
aws logs tail /ecs/{name_prefix}-inventory-api --follow
```

## File Structure

```
infrastructure/
├── main.tf              # Provider, common locals
├── customer_site.tf      # Customer API: ECR, ECS Fargate, ALB, S3 static site
├── employee_site.tf      # Employee BFF: ECR, ECS Fargate, ALB, S3 static site
├── fastapi_site.tf        # Inventory API: ECR, ECS Fargate (registers into the NLB in api_gateway.tf)
├── api_gateway.tf        # Vendor-facing API Gateway, internal NLB, VPC Link
├── security.tf           # Security groups, VPC data sources
├── iam.tf                # Shared ECS execution/task role lookup
├── cognito.tf             # Employee user pool + app client
├── lambda.tf              # Report Lambda + EventBridge Scheduler group
├── dynamodb.tf            # DynamoDB table definitions
├── s3.tf                  # Image + report buckets
├── deploy.tf              # Deployment automation (build/push/deploy, seeding)
├── outputs.tf              # Terraform outputs
├── variables.tf            # Input variables
├── terraform.tf             # Terraform/provider version constraints
└── README.md                # This file
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all ECS services, ALBs/NLB, S3 buckets, Cognito user pool, the report Lambda, and DynamoDB tables. Data in DynamoDB will be lost.

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

- [S3 Configuration Guide](S3_CONFIGURATION.md)
- [AWS Academy Documentation](https://awsacademy.instructure.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Project Root README](../README.md)
