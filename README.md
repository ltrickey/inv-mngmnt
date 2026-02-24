# Grocery Store Inventory Management
Homework series for CPSC 5910 Cloud Computing Seattle University

By Lynn Trickey with assistance from Cursor AI agent

## Testing for Employee Website Homework
**Changed since last homework submission**
* Moved customer site backend from EC2 to docker image with ECR & ECS
* Moved front end to S3 bucket
* Changed S3 bucket hosting images to public to increase load time - extra security not needed.

### Prereqesites
- AWS credentials set
- Install jq 
- Install Docker Desktop

### How to test
1. Follow pre-deployment setup instructions to set SSH key and AWS credentials (if not already set)
2. Make sure Docker Desktop is running
3. Deploy app to AWS: 
```bash
cd /infrastructure
terraform init
terraform apply
```
(See [Deployment Process](#deployment-process) for more detailed instructions)

3. Test new API gateway endpoints by running test_api_gateway.sh locally in terminal.  Script runs locally in terminal and fetches API endpoint and API key from Terraform outputs.

```bash
cd .. # go to root directory
./scripts/test_api_gateway.sh
```

4. Hit updated Website endpoint at customer_site_url in outputs, functionality should be unchanged - search for products or products in a given store.

## Pre-Deployment Setup
**AWS Credentials and SSH Key are required to run Terraform Deployment**

Before running Terraform, you need to configure your AWS credentials and SSH key. If you're using temporary credentials (common with AWS Academy/AWS Educate), you'll need to set three environment variables:

### Getting AWS Credentials

**AWS Academy/AWS Educate:**
   - Download the credentials CSV file from your AWS Academy account
   - The file contains: Access Key ID, Secret Access Key, and Session Token

### Setting AWS Credentials

Either set with export, or configure in ~./aws/credentials file like so:
```bash
[default]
aws_access_key_id = YOUR_AWS_KEY_ID
aws_secret_access_key = YOUR_AWS_SECRET_ACCESS_KEY
aws_session_token = YOUR_SESSION_TOKEN_HERE
```

**For temporary credentials (Access Key starts with "ASIA"):**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_SESSION_TOKEN="your-session-token"
```

**For permanent credentials:**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
# AWS_SESSION_TOKEN not needed for permanent credentials
```

### Verifying Credentials

Check if your credentials are set:
```bash
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
echo $AWS_SESSION_TOKEN  # Only needed for temporary credentials
```

**Note:** Temporary credentials expire. If you get "InvalidClientTokenId" errors, you may need to download fresh credentials from AWS Academy.

## SSH Key Setup

To deploy to EC2 instances, you need an SSH key pair. The Terraform configuration uses the key name specified in `infrastructure/variables.tf` (default: `vockey`).

### Downloading and Setting Up Your SSH Key

1. **Download the private key file:**
   - Download `vockey.pem` (or your key pair's `.pem` file) from AWS Academy or AWS Console
   - Save it to `~/.ssh/vockey.pem` 

2. **Set correct permissions:**
   ```bash
   chmod 600 ~/.ssh/vockey.pem
   ```
   
   **Important:** SSH requires private key files to have permissions `0600` (readable/writable by owner only). If permissions are too open (e.g., `0644`), SSH will refuse to use the key and you'll get a "Permission denied" error.

3. **Verify permissions:**
   ```bash
   ls -l ~/.ssh/vockey.pem
   ```
   Should show: `-rw-------` (owner read/write only)

**Troubleshooting:**
- If you get "WARNING: UNPROTECTED PRIVATE KEY FILE!" or "bad permissions", run `chmod 600 ~/.ssh/vockey.pem`
- If you download a new key file, remember to set permissions again
- Make sure the key name in Terraform variables matches your actual key name in AWS

## Local Development

For local development, both the Flask WebApp and FastAPI Inventory Service can run without DynamoDB by using JSON seed files from the `seed_data/` directory.

### Environment Variables (.env files)

Both services include `.env` files for local development configuration:

**Flask WebApp (`server/.env`):**
```bash
# Disable DynamoDB for local development (use JSON seed files instead)
USE_DYNAMODB=0

# Point Flask to the FastAPI inventory service for stock/sales data
INVENTORY_API_BASE_URL=http://127.0.0.1:9000
```

**FastAPI Inventory Service (`inventory_api/.env`):**
```bash
# Disable DynamoDB for local development (use JSON seed files from ../seed_data instead)
USE_DYNAMODB=0
```

Both services automatically load their respective `.env` files if `python-dotenv` is installed (included in `requirements.txt`). You don't need to manually export these variables unless you prefer not to use the `.env` files.

### Running Locally

**1. Start the FastAPI Inventory Service:**

```bash
cd inventory_api
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt  # Includes python-dotenv

# The .env file will be loaded automatically
# Run the service
uvicorn main:app --reload --port 9000
```

The inventory API will read from `../seed_data/products_by_store.json` when `USE_DYNAMODB=0`.

**2. Start the Flask WebApp:**

In a separate terminal:

```bash
cd server
python -m venv .venv  # If you haven't already
source .venv/bin/activate
pip install -r requirements.txt  # Install Flask dependencies (includes python-dotenv)

# The .env file will be loaded automatically by Flask
# Run Flask (adjust command based on how you start Flask)
python app.py
# or: flask run --port 8000
```

The Flask app will:
- Read products and stores from `../seed_data/products.json` and `../seed_data/stores.json`
- Forward stock/sales requests to the FastAPI inventory service at `http://127.0.0.1:9000`

**3. Start the React Frontend (optional for full-stack testing):**

```bash
cd site
npm install
npm run dev
```

The React app will connect to Flask at `http://localhost:8000`.

### Notes

- **Seed data location:** All seed data files (`products.json`, `stores.json`, `products_by_store.json`, `categories.json`) are located at the repo root in `seed_data/` (moved from `server/seed_data/`).
- **No AWS credentials needed:** When `USE_DYNAMODB=0`, neither service requires AWS credentials or DynamoDB access.
- **Service communication:** Flask calls the FastAPI inventory service for all stock/sales data. Make sure the inventory service is running before starting Flask.

## Architecture

```
Customer Site:
  React SPA (S3)  →  Flask API (ECS Fargate / Docker)  →  DynamoDB
                                                        →  Inventory API (EC2)
                                                        →  S3 Product Images

Employee Site:
  React SPA (S3)  →  Flask BFF (ECS Fargate / Docker)  →  Customer API (ECS Fargate)
                                                        →  Inventory API (EC2)

Inventory API:
  FastAPI (EC2)  →  DynamoDB

Public API:
  API Gateway  →  Inventory API (EC2)
```

## Deployment Process

### Prerequisites

The following must be installed and available on the machine running `terraform apply`:

- **Docker Desktop** — must be running. Docker is used to build and push container images to ECR for both the customer and employee sites.
- **Node.js 18+** — used to build the React frontends before uploading to S3.
- **AWS CLI** — configured with valid credentials (`~/.aws/credentials`). For Learner Lab, re-copy credentials each session.
- **Terraform** — the infrastructure is defined in `infrastructure/`.
- **SSH Key** — required for deploying the Inventory API to its EC2 instance (see [SSH Key Setup](#ssh-key-setup)).

### Quick Start

```bash
cd infrastructure
terraform init    # first time only
terraform apply   # builds, packages, and deploys everything
```

You will need to input `yes` to allow `terraform apply` to make the required changes.

### What Terraform Does

1. Creates AWS infrastructure (ECS Fargate clusters, ALBs, ECR, S3 buckets, EC2 for Inventory API, DynamoDB, API Gateway, Cognito, etc.)
2. Uploads product images to S3
3. Deploys the Inventory API to EC2 via SCP
4. Seeds DynamoDB tables with product data
5. Builds the Customer API Docker image locally and pushes to ECR
6. Builds the Customer React frontend and uploads to S3
7. Deploys customer ECS service
8. Builds the Employee BFF Docker image locally and pushes to ECR
9. Builds the Employee React frontend and uploads to S3
10. Deploys employee ECS service

### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `deploy_customer_site.sh` | Builds Customer API Docker image, pushes to ECR, builds React frontend, uploads to S3, redeploys ECS |
| `deploy_employee_site.sh` | Builds Employee BFF Docker image, pushes to ECR, builds React frontend, uploads to S3, redeploys ECS |
| `seed_dynamodb.sh` | Seeds DynamoDB tables with product data |
| `upload_images_to_s3.sh` | Uploads product images to S3 |
| `package_inventory_api.sh` | Packages Inventory API for EC2 deployment |
| `deploy_inventory_api_remote.sh` | Deploys Inventory API to EC2 |

### Post-Deployment

**Access the applications:**
```bash
terraform output customer_site_url    # Customer site (S3 static website)
terraform output customer_api_alb_url  # Customer API (ALB)
terraform output employee_site_url     # Employee site (S3 static website)
terraform output employee_bff_alb_url  # Employee BFF API (ALB)
```

### DynamoDB Seeding

**Fully Automated:** Tables are automatically seeded during `terraform apply` from `seed_data/` directory on your local machine. No manual steps required.

**What Gets Seeded:**
- 100 products
- 5 stores
- 85 inventory items (products by store)
- 64 categories

**Manual Re-seeding (optional, only if you need to reset data):**
```bash
INFRASTRUCTURE_DIR=./infrastructure ./scripts/seed_dynamodb.sh
```

**Note:** Seeding runs automatically whenever DynamoDB tables are created or recreated by Terraform.