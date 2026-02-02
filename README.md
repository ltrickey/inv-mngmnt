# Customer Website
Homework series for CPSC 5910 Cloud Computing Seattle University

Written by Lynn Trickey with assistance from Cursor AI agent

## AWS Credentials Setup

Before running Terraform, you need to configure your AWS credentials. If you're using temporary credentials (common with AWS Academy/AWS Educate), you'll need to set three environment variables:

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

### Getting Credentials

1. **AWS Academy/AWS Educate:**
   - Download the credentials CSV file from your AWS Academy account
   - The file contains: Access Key ID, Secret Access Key, and Session Token
   - Set all three environment variables

2. **AWS CLI Configuration (Alternative):**
   ```bash
   aws configure
   ```
   This will prompt for credentials and save them to `~/.aws/credentials`

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
   - Save it to `~/.ssh/vockey.pem` (or your preferred location)

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

DynamoDB tables are seeded from `server/seed_data` **as part of the Terraform deployment workflow**. When you run `terraform apply`, the provisioner runs `scripts/seed_dynamodb.sh` before packaging and deploying to EC2. The script loads `products.json`, `stores.json`, `stock.json`, and `sales.json` into the tables named by Terraform (`name_prefix-products`, `-stores`, `-stock`, `-sales`).

**Requirements:** `jq` and AWS CLI installed and configured (same credentials as Terraform).

**To seed manually** (e.g. after changing seed data without re-deploying):
```bash
./scripts/seed_dynamodb.sh
```
Optional env vars: `INFRASTRUCTURE_DIR`, `SEED_DATA_DIR`, `AWS_REGION`.