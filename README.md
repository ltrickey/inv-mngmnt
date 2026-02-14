# Grocery Store Inventory Management
Homework series for CPSC 5910 Cloud Computing Seattle University

By Lynn Trickey with assistance from Cursor AI agent

## Testing for Point of Sale API homework
**Changed since last homework submission**
* Updated data model
* Added FastAPI inventory API hosted on Ec2 instance
* Wired Flask WebServer to fetch stock information from FastAPI instead of DynamoDB table directly. _Note: the website still does access other DynamoDB tables directly - to be addressed in future_
* Added API Gateway endpoints 

### How to test
1. Follow pre-deployment setup instructions to set SSH key and AWS credentials (if not already set)
2. Deploy app to AWS: 
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

4. Hit updated Website endpoint at service_url in outputs, functionality should be unchanged - search for products or products in a given store.

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

### Deployment Process

**Quick Start:**
```bash
cd infrastructure
terraform apply  # Automatically builds, packages, and deploys everything
```

**What Terraform Does:**
1. Creates AWS infrastructure (EC2, security groups, DynamoDB, S3, API Gateway, etc.)
2. Builds React app locally (requires Node.js)
3. Packages applications into deployment archives
4. Deploys Product Catalogue and Inventory API to EC2 via SCP
5. Uploads product images to S3
6. **Seeds DynamoDB tables automatically** (no manual steps required)

**Manual Deployment (for updates without Terraform):**
```bash
./scripts/package.sh        # Build & package locally
./scripts/deploy_remote.sh  # Deploy to existing EC2
```

### Deployment Scripts

| Script | Runs On | Purpose |
|--------|---------|---------|
| `package.sh` | Local | Builds React (`npm run build`), packages Flask + images into ZIP |
| `deploy_remote.sh` | Local | Copies ZIP to EC2, triggers installation |
| `deploy.sh` | EC2 | Extracts files, installs dependencies, starts service |
| `seed_dynamodb.sh` | Local (via Terraform) | Seeds DynamoDB tables with product data |
| `package_inventory_api.sh` | Local | Packages Inventory API into ZIP |
| `deploy_inventory_api_remote.sh` | Local | Copies Inventory API ZIP to EC2, triggers installation |

### Requirements

- **Local:** Node.js (for React build), AWS credentials, SSH key
- **EC2:** Python 3, AWS CLI, IAM role (automatically configured by Terraform)

### Post-Deployment

**Access the application:**
```bash
terraform output service_url  # Get http://<EC2_PUBLIC_DNS>:8000
```

**Check service status:**
```bash
ssh -i ~/.ssh/vockey.pem ec2-user@<EC2_HOST> "sudo systemctl status product_catalogue_flask"
```

**View logs:**
```bash
ssh -i ~/.ssh/vockey.pem ec2-user@<EC2_HOST> "sudo journalctl -u product_catalogue_flask -f"
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
cd /
INFRASTRUCTURE_DIR=./infrastructure ./scripts/seed_dynamodb.sh
```

**Note:** Seeding runs automatically whenever DynamoDB tables are created or recreated by Terraform.