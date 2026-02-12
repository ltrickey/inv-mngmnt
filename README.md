# Grocery Store Inventory Management
Homework series for CPSC 5910 Cloud Computing Seattle University

By Lynn Trickey with assistance from Cursor AI agent

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

## Deployment Process

Before running deployment, you must have the correct aws credentials and ssh key set as described above.  Otherwise the deployment will fail.

The deployment is fully automated through Terraform. To deploy:

```bash
cd /infrastructure
terraform init
terraform apply
```

You will need to input `yes` to allow `terraform apply` to make the required changes.

### What Happens When You Run `terraform apply`

1. **Terraform Creates Infrastructure:**
   - Creates EC2 instance
   - Sets up security groups
   - Configures networking

2. **Automatic Build and Deployment:**

   After the EC2 instance is created, Terraform automatically triggers the deployment process.  

   **Step 1: Builds React Application**
   - Runs `npm install` (if `node_modules` doesn't exist)
   - Runs `npm run build` to create production build in `site/dist/`
   - Build happens on your **local machine** (where Terraform runs)
   - Requires Node.js installed locally

   **Step 2: Packages Everything**
   - Packages Flask server files (`server/`)
   - Packages React production build (`site/dist/`)
   - Packages product images (`infrastructure/images/`)
   - Creates deployment archive (`product_catalogue.zip`)

   **Step 3: Deploys to EC2**
   - Copies package to EC2 instance via SCP
   - Extracts files to `/opt/product_catalogue/`
   - Sets up Python virtual environment
   - Installs Python dependencies (Flask, Gunicorn, etc.)
   - Seeds DynamoDB tables from `server/seed_data` (on EC2, using instance profile)
   - Creates and enables systemd service
   - Starts the Flask application

### Deployment Commands

**Full automated deployment:**
```bash
cd infrastructure
terraform apply
```

**Manual deployment (if needed):**
```bash
# Build and package locally
./scripts/package.sh

# Deploy to EC2
./scripts/deploy_remote.sh
```

### Deployment Scripts Overview

The deployment process uses three scripts, each with a specific role:

**1. `package.sh` (Local only - no EC2 interaction)**
- **Purpose:** Builds and packages the application locally
- **Responsibilities:**
  - Builds React application (`npm install`, `npm run build`)
  - Packages Flask server files
  - Packages React production build
  - Packages product images
  - Creates ZIP archive (`deploy/product_catalogue.zip`)
- **Output:** Creates `deploy/product_catalogue.zip` ready for deployment

**2. `deploy_remote.sh` (Handles all EC2 interaction)**
- **Purpose:** Orchestrates deployment to EC2 instance
- **Responsibilities:**
  - Gets EC2 instance details from Terraform outputs
  - Finds SSH key for EC2 access
  - Copies package to EC2 via SCP (`/tmp/product_catalogue.zip`)
  - Waits for SSH availability
  - Connects to EC2 and extracts package
  - Runs `deploy.sh` on EC2 instance

**3. `deploy.sh` (Runs on EC2 instance)**
- **Purpose:** Sets up the application on the EC2 instance
- **Responsibilities:**
  - Extracts package to `/opt/product_catalogue/`
  - Creates Python virtual environment
  - Installs Python dependencies
  - Seeds DynamoDB from `server/seed_data` (when using DynamoDB; installs `jq` if needed)
  - Creates systemd service file
  - Starts and enables Flask service
- **Runs on:** EC2 instance (executed via SSH from `deploy_remote.sh`)


### What Gets Built

- **React App:** Production build created locally (`site/dist/`)
- **Flask App:** Python files packaged (no compilation needed)
- **Images:** Product images copied to deployment package
- **Everything:** Packaged into `product_catalogue.zip` and deployed to EC2

### Important Notes

- **Build Location:** React app is built on your **local machine**, not on EC2
- **Requirements:** You need Node.js installed locally for the build process
- **EC2 Requirements:** EC2 only needs Python (for Flask) - no Node.js required
- **Auto-restart:** The application automatically restarts on EC2 reboot and on failure

### Accessing Your Application

After deployment, access your application at:
```
http://<EC2_PUBLIC_DNS>:8000
```

Get the URL from Terraform output:
```bash
cd infrastructure
terraform output service_url
```

### Checking Deployment Status

Check if the service is running on EC2:
```bash
ssh -i ~/.ssh/vockey.pem ec2-user@<EC2_HOST> "sudo systemctl status product_catalogue_flask"
```

View logs:
```bash
ssh -i ~/.ssh/vockey.pem ec2-user@<EC2_HOST> "sudo journalctl -u product_catalogue_flask -f"
```

### Seeding DynamoDB

DynamoDB tables are seeded **on the EC2 instance** during `deploy.sh`, using the instance's IAM role (no local AWS credentials needed for seeding). The seed script runs after the package is extracted and loads `products.json`, `stores.json`, `products_by_store.json`, and `categories.json` from `server/seed_data` into the tables (`name_prefix-products`, `-stores`, `-products-by-store`, and `categories`). EC2 needs `jq` and the AWS CLI; `deploy.sh` will install `jq` via `yum`/`dnf` if missing. In `products.json`, each product has a **category_path** field: `"<secondary>#<tertiary>#<barcode>"` (e.g. `"Cheese#NONE#0123456789017"`). Missing secondary or tertiary categories are stored as the literal `"NONE"`.

**To seed manually from your machine** (e.g. after changing seed data without re-deploying):
```bash
INFRASTRUCTURE_DIR=./infrastructure ./scripts/seed_dynamodb.sh
```
Or on EC2 (with `DYNAMODB_PRODUCTS_TABLE` set in the environment or in the Flask env file):
```bash
SEED_DATA_DIR=/opt/product_catalogue/server/seed_data DYNAMODB_PRODUCTS_TABLE=your-prefix-products /opt/product_catalogue/scripts/seed_dynamodb.sh
```
Optional env vars: `NAME_PREFIX` or `DYNAMODB_PRODUCTS_TABLE`, `SEED_DATA_DIR`, `INFRASTRUCTURE_DIR` (for local Terraform output), `AWS_REGION`.