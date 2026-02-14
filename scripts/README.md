# Deployment Scripts

This directory contains scripts for building, packaging, and deploying the Product Catalogue application and Inventory API to AWS EC2 instances.

## Overview

The deployment process consists of two main components:

1. **Product Catalogue** - Flask application serving React frontend (port 8000)
2. **Inventory API** - FastAPI service for inventory management (port 9000)

## Quick Start

### Deploy Everything

To package and deploy both services in one command:

```bash
./scripts/deploy_all.sh
```

This will:
1. Build and package the Product Catalogue (React + Flask)
2. Package the Inventory API
3. Deploy Product Catalogue to its EC2 instance
4. Deploy Inventory API to its EC2 instance

### Deploy Individual Services

#### Product Catalogue

```bash
# Step 1: Package the application
./scripts/package.sh

# Step 2: Deploy to EC2
./scripts/deploy_remote.sh
```

#### Inventory API

```bash
# Step 1: Package the API
./scripts/package_inventory_api.sh

# Step 2: Deploy to EC2
./scripts/deploy_inventory_api_remote.sh
```

## Script Reference

### Product Catalogue Scripts

| Script | Description | Runs On |
|--------|-------------|---------|
| `package.sh` | Builds React app and packages Flask + React for deployment | Local machine |
| `deploy_remote.sh` | Copies package to EC2 and orchestrates deployment | Local machine |
| `deploy.sh` | Extracts package and sets up Flask service on EC2 | EC2 instance |

### Inventory API Scripts

| Script | Description | Runs On |
|--------|-------------|---------|
| `package_inventory_api.sh` | Packages Inventory API for deployment | Local machine |
| `deploy_inventory_api_remote.sh` | Copies package to EC2 and orchestrates deployment | Local machine |
| `deploy_inventory_api.sh` | Extracts package and sets up FastAPI service on EC2 | EC2 instance |

### Utility Scripts

| Script | Description |
|--------|-------------|
| `deploy_all.sh` | Deploys both Product Catalogue and Inventory API |
| `seed_dynamodb.sh` | Seeds DynamoDB tables with initial data |
| `check_status.sh` | Checks the status of running services |
| `generate_product_images.py` | Generates product images (if needed) |

## Prerequisites

Before running deployment scripts, ensure:

1. **Terraform Infrastructure** - EC2 instances must be created first:
   ```bash
   cd infrastructure
   terraform init
   terraform apply
   ```

2. **SSH Key** - Your AWS key pair (default: `vockey.pem`) must be available at:
   - `~/.ssh/vockey.pem`, or
   - `~/.ssh/vockey`, or
   - `infrastructure/vockey.pem`

3. **Node.js** - Required for building React app (Product Catalogue only)
   ```bash
   node --version  # Should be v18+
   ```

4. **Python 3** - Required for both services
   ```bash
   python3 --version  # Should be 3.9+
   ```

## Deployment Details

### Product Catalogue Deployment

**Deployed to:** `/opt/product_catalogue/`

**Service:** `product_catalogue_flask.service`

**Port:** 8000

**Contents:**
- React build (`site-dist/`)
- Flask server (`server/`)
- Product images (`infrastructure/images/`)
- Seed data (`server/seed_data/`)

**Environment Variables:**
- Set in `/etc/product_catalogue_flask.env`
- Automatically configured during deployment

### Inventory API Deployment

**Deployed to:** `/opt/inventory_api/`

**Service:** `inventory_api.service`

**Port:** 9000

**Contents:**
- FastAPI application (`main.py`, `inventory.py`)
- Requirements (`requirements.txt`)

**Environment Variables:**
- Set in `/etc/inventory_api.env`
- Automatically configured during deployment

**Network Access:**
- Only accessible from the Product Catalogue EC2 instance via private IP
- Not publicly accessible (security group restricts access)

## Configuration

### DynamoDB Integration

Both services automatically detect and use DynamoDB when deployed to EC2- **Products Table:** `{NAME_PREFIX}-products`
- **Products by Store Table:** `{NAME_PREFIX}-products_by_store`

Where `{NAME_PREFIX}` is derived from Terraform outputs (e.g., `product-catalogue-test`).

### Environment Variables

Variables are automatically set during deployment from Terraform outputs:

- `USE_DYNAMODB=1` - Enable DynamoDB mode
- `DYNAMODB_PRODUCTS_TABLE` - Products table name
- `NAME_PREFIX` - Resource naming prefix
- `AWS_REGION` - AWS region (default: us-east-1)

## Troubleshooting

### Check Service Status

SSH into the EC2 instance and check systemd services:

```bash
# Product Catalogue
sudo systemctl status product_catalogue_flask

# Inventory API
sudo systemctl status inventory_api
```

### View Service Logs

```bash
# Product Catalogue
sudo journalctl -u product_catalogue_flask -f

# Inventory API
sudo journalctl -u inventory_api -f
```

### Restart Services

```bash
# Product Catalogue
sudo systemctl restart product_catalogue_flask

# Inventory API
sudo systemctl restart inventory_api
```

### Check Network Connectivity

From the Product Catalogue EC2 instance, test connectivity to Inventory API:

```bash
# Get Inventory API private IP from Terraform outputs
terraform -chdir=infrastructure output inventory_api_private_ip

# Test connection
curl http://<PRIVATE_IP>:9000/health
```

## Security Notes

1. **SSH Keys** - Keep your `.pem` files secure with proper permissions:
   ```bash
   chmod 400 ~/.ssh/vockey.pem
   ```

2. **Network Isolation** - The Inventory API is only accessible from the Product Catalogue instance, not from the public internet.

3. **IAM Instance Profile** - Both EC2 instances use `LabInstanceProfile` for DynamoDB access.

4. **Security Groups:**
   - Product Catalogue: Allows public access on port 8000 and SSH on port 22
   - Inventory API: Only allows access from Product Catalogue security group on port 9000, SSH on port 22

## Manual Deployment Steps

If you need to deploy manually without scripts:

### Product Catalogue

1. Build React app: `cd site && npm run build`
2. Package: `cd .. && zip -r package.zip server/ site/dist/ scripts/`
3. Copy to EC2: `scp package.zip ec2-user@<PUBLIC_IP>:/tmp/`
4. SSH to EC2: `ssh ec2-user@<PUBLIC_IP>`
5. Extract and run: `unzip package.zip && ./deploy.sh`

### Inventory API

1. Package: `cd inventory_api && zip -r inventory_api.zip .`
2. Copy to EC2: `scp inventory_api.zip ec2-user@<PUBLIC_IP>:/tmp/`
3. SSH to EC2: `ssh ec2-user@<PUBLIC_IP>`
4. Extract and run: `unzip inventory_api.zip && ./deploy.sh`

## Additional Resources

- [Product Catalogue README](../server/README.md)
- [Inventory API README](../inventory_api/README.md)
- [Infrastructure README](../infrastructure/README.md)
