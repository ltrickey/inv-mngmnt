# Grocery Store Inventory Management
Homework series for CPSC 5910 Cloud Computing Seattle University

By Lynn Trickey with assistance from Cursor AI agent

**Changed since last homework submission**
* Added DynamoDB tables for sales records
* Added API in inventory_api to record sales from store POS systems
* Added view in employee_site to set up reports to run
* Added Lambda to generate repts under report_lambda
* Added EventBridge to schedule runing reports lambda
* Added S3 Config to save & load past reports

## Testing for Inventory Management Tool

1. Follow pre-deployment setup instructions to set SSH key and AWS credentials (if not already set)
1. Make sure Docker Desktop is running
1. Deploy app to AWS: 
   ```bash
   cd /infrastructure
   terraform init
   terraform apply
   ```
   (See [Deployment Process](#deployment-process) for more detailed instructions)

1. Once deployment is complete, Create user in Cognito User pool for new Employee website, submitting an email to create a user with.

   ```bash
   cd .. # go to root directory
   ./scripts/create_employee_user.sh --email <ENTER YOUR EMAIL HERE>
   ```

   Output should look like this:
   ```bash
   User created successfully!
   Username:           your_email
   Email:              your_email
   Temporary password: j8@wVFbN0j7T
   Status:             FORCE_CHANGE_PASSWORD
   ```

1. Use the temporary password to login at the employee site url (part of terraform outputs).  It should be in this format:
   ```
   employee_site_url = "http://product-catalogue-test-employee-site-<aws_account_id>.s3-website-us-east-1.amazonaws.com"
   ````

1. Once logged in, choose the 'reports' tab at the top of the page
1. Click add new schedule
1. Setup a report to run every minute (filtered by store or category)

1. Run the traffic generator to create some sales.  Each call picks a random store, fetches its in-stock inventory, and submits a basket of 1–3 random items. 
All stores and products are eligible on every run; with enough calls (e.g. `--calls 50` across 5 stores) coverage is well-distributed.

```bash
# Default: 20 calls at 2/sec
./scripts/traffic_generator.sh

# Custom rate and call count
./scripts/traffic_generator.sh --calls 50 --rate 5
```
1. Run restock if needed
Resets inventory quantities after the traffic generator depletes stock.

```bash
# Restock all items to 500 units (default)
./scripts/restock.sh

# Restock only depleted items (quantity <= 10)
./scripts/restock.sh --low-only --threshold 10
```

1. Verify API Gateway endpoints still work (previous assignment, optional)

   ```bash
   cd .. # go to root directory
   ./scripts/test_api_gateway.sh
   ```

### Prerequisites

Everything below must be installed and configured on your local machine for the deployment and scripts to work.

- **AWS credentials** — Set as environment variables or in `~/.aws/credentials`. See [Pre-Deployment Setup](#pre-deployment-setup) and [Getting AWS Credentials](#getting-aws-credentials).
- **Terraform** — Used by `terraform apply` and by scripts that read Terraform outputs.
- **AWS CLI** — Used by deploy scripts, `create_employee_user.sh`, `seed_dynamodb.sh`, and others. Configure with the same credentials as above.
- **Node.js 18+** and **npm** — Used to build the customer and employee React frontends during deploy.
- **jq** — Required by `seed_dynamodb.sh` (and by Terraform-triggered seeding during `terraform apply`).
- **Docker Desktop** — Must be installed and running. Used to build and push container images to ECR for the customer and employee sites.
- **SSH key** — Required for Inventory API EC2 deployment and for `check_status.sh` / `check_and_seed_db.sh`. See [SSH Key Setup](#ssh-key-setup).

Optional for some scripts: **Python 3** (e.g. for `test_api_gateway.sh` and manual Inventory API packaging).

#### Installing jq

**macOS (Homebrew):**
```bash
brew install jq
```

**Windows (PowerShell as Administrator):**
- Using Chocolatey: `choco install jq`
- Using winget: `winget install jq.jq`
- Or download the Windows binary from [jqlang.github.io/jq](https://jqlang.github.io/jq/) and add the folder containing `jq.exe` to your PATH.

**Linux:**
- Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y jq`
- RHEL/CentOS/Fedora: `sudo yum install -y jq` or `sudo dnf install -y jq`
- Arch: `sudo pacman -S jq`

Verify: `jq --version`

#### Installing Docker Desktop

**macOS:**
- Download the appropriate installer (Apple Silicon or Intel) from [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/).
- Open the `.dmg`, drag Docker to Applications, then open Docker from Applications. Allow privileged helper when prompted.
- Ensure Docker is running (whale icon in the menu bar) before running `terraform apply` or deploy scripts.

**Windows:**
- Download the installer from [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/). You need WSL 2; the installer can enable it.
- Run the installer, restart if asked, then start “Docker Desktop” from the Start menu.
- Ensure Docker is running before `terraform apply` or deploy scripts.

**Linux:**
- Follow [Install Docker Engine](https://docs.docker.com/engine/install/) for your distribution. For the full Desktop experience (GUI), use [Docker Desktop for Linux](https://docs.docker.com/desktop/install/linux-install/).
- Start the Docker service (e.g. `sudo systemctl start docker` or start Docker Desktop) before running Terraform or deploy scripts.

Verify: `docker run hello-world`

#### Other tools (Terraform, AWS CLI, Node.js)

- **Terraform:** [Install Terraform](https://developer.hashicorp.com/terraform/downloads) — e.g. macOS: `brew install terraform`; Windows: `choco install terraform` or download the binary.
- **AWS CLI:** [Install or update the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) — e.g. macOS: `brew install awscli`; Windows: `msi` installer or `pip install awscli`.
- **Node.js:** [Node.js downloads](https://nodejs.org/) (LTS 18+). macOS: `brew install node`; Windows: use the installer or `winget install OpenJS.NodeJS.LTS`.


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

### Terraform remove state (if AWS Learner Lab closes w/o running terraform destroy)
1. Back up the old state (just in case):


cp infrastructure/terraform.tfstate infrastructure/terraform.tfstate.old-lab
cp infrastructure/.terraform.lock.hcl infrastructure/.terraform.lock.hcl.bak 2>/dev/null || true

2. Delete the stale state:


rm -f infrastructure/terraform.tfstate
rm -f infrastructure/terraform.tfstate.backup
rm -rf infrastructure/.terraform