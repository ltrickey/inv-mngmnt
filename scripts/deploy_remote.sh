#!/bin/bash
# Remote deployment script - handles all EC2 interaction
# This script copies the package to EC2 and runs deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Allow INFRASTRUCTURE_DIR to be overridden by environment variable (useful when called from Terraform)
INFRASTRUCTURE_DIR="${INFRASTRUCTURE_DIR:-$PROJECT_ROOT/infrastructure}"
OUTPUT_DIR="$PROJECT_ROOT/deploy"
PACKAGE_NAME="product_catalogue.zip"
EC2_USER="ec2-user"

echo "=========================================="
echo "REMOTE DEPLOYMENT TO EC2"
echo "=========================================="

# Check if package exists
PACKAGE_PATH="$OUTPUT_DIR/$PACKAGE_NAME"
if [ ! -f "$PACKAGE_PATH" ]; then
    echo "Error: Package not found at $PACKAGE_PATH"
    echo "Please run ./scripts/package.sh first to build and package the application"
    exit 1
fi

echo "Package found: $PACKAGE_PATH"
echo ""

# Get EC2 instance details from Terraform output
# Use -chdir to run terraform commands from the infrastructure directory where terraform.tfstate is located
if [ ! -d "$INFRASTRUCTURE_DIR" ]; then
    echo "Error: Infrastructure directory not found: $INFRASTRUCTURE_DIR"
    exit 1
fi

# Retry mechanism: Wait for Terraform outputs to become available
# This is needed because terraform_data runs immediately after EC2 creation, and outputs may not be ready yet
echo "Retrieving EC2 instance details from Terraform output..."
EC2_PUBLIC_IP=""
EC2_PUBLIC_DNS=""
KEY_PAIR=""

for i in {1..30}; do
    EC2_PUBLIC_IP=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw ec2_instance_public_ip 2>/dev/null || echo "")
    EC2_PUBLIC_DNS=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw ec2_instance_public_dns 2>/dev/null || echo "")
    KEY_PAIR=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw ec2_key_pair 2>/dev/null || echo "vockey")
    
    if [ -n "$EC2_PUBLIC_IP" ] || [ -n "$EC2_PUBLIC_DNS" ]; then
        echo "✓ EC2 instance details retrieved"
        break
    fi
    
    if [ $i -lt 30 ]; then
        echo "  Waiting for Terraform outputs to become available... (attempt $i/30)"
        sleep 1
    fi
done

if [ -z "$EC2_PUBLIC_IP" ] && [ -z "$EC2_PUBLIC_DNS" ]; then
    echo "Error: Could not retrieve EC2 instance details from Terraform output after 30 attempts."
    echo "Current directory: $(pwd)"
    echo "Infrastructure directory: $INFRASTRUCTURE_DIR"
    echo "Terraform state file exists: $([ -f "$INFRASTRUCTURE_DIR/terraform.tfstate" ] && echo 'yes' || echo 'no')"
    echo ""
    echo "Trying to get outputs from infrastructure directory..."
    terraform -chdir="$INFRASTRUCTURE_DIR" output 2>&1 || true
    echo ""
    echo "Make sure Terraform has been applied and the infrastructure directory is accessible."
    exit 1
fi

EC2_HOST="${EC2_PUBLIC_DNS:-$EC2_PUBLIC_IP}"
echo "EC2 Instance: $EC2_HOST"
echo ""

# Find SSH key
SSH_KEY=""
if [ -f "$HOME/.ssh/${KEY_PAIR}.pem" ]; then
    SSH_KEY="$HOME/.ssh/${KEY_PAIR}.pem"
elif [ -f "$HOME/.ssh/${KEY_PAIR}" ]; then
    SSH_KEY="$HOME/.ssh/${KEY_PAIR}"
elif [ -f "$INFRASTRUCTURE_DIR/${KEY_PAIR}.pem" ]; then
    SSH_KEY="$INFRASTRUCTURE_DIR/${KEY_PAIR}.pem"
else
    echo "Error: Could not find SSH key for ${KEY_PAIR}"
    echo "Please set SSH_KEY environment variable"
    exit 1
fi

echo "Using SSH key: $SSH_KEY"
echo ""

# ============================================
# STEP 1: COPY PACKAGE TO EC2 VIA SCP
# ============================================
echo "=========================================="
echo "COPYING PACKAGE TO EC2 INSTANCE"
echo "=========================================="
echo "EC2 Instance: $EC2_HOST"
echo "EC2 User: $EC2_USER"
echo "Package: $PACKAGE_PATH"
echo ""
echo "COPY DESTINATION ON EC2:"
echo "  Temporary location: /tmp/$PACKAGE_NAME"
echo "  (Will be extracted to: /opt/product_catalogue/)"
echo ""

echo "Copying package to EC2 instance..."
scp -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$PACKAGE_PATH" \
    "$EC2_USER@$EC2_HOST:/tmp/"

if [ $? -ne 0 ]; then
    echo ""
    echo "✗ Failed to copy package to EC2 instance"
    exit 1
fi

echo "✓ Package successfully copied to EC2 instance!"
echo ""

# Wait for SSH to be available (in case instance just started)
echo "Waiting for SSH to be available..."
for i in {1..30}; do
    if ssh -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=5 \
        "$EC2_USER@$EC2_HOST" "echo 'SSH ready'" &>/dev/null; then
        echo "✓ SSH is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Error: SSH not available after 30 attempts"
        exit 1
    fi
    sleep 2
done

# Get DynamoDB table name and region for Flask (so EC2 uses DynamoDB for products)
NAME_PREFIX=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw name_prefix 2>/dev/null || echo "")
AWS_REGION=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw aws_region 2>/dev/null || echo "us-east-1")
DYNAMODB_PRODUCTS_TABLE=""
[ -n "$NAME_PREFIX" ] && DYNAMODB_PRODUCTS_TABLE="${NAME_PREFIX}-products"

# ============================================
# STEP 2: DEPLOY ON EC2 INSTANCE VIA SSH
# ============================================
echo ""
echo "=========================================="
echo "DEPLOYING ON EC2 INSTANCE"
echo "=========================================="
echo ""

# Run deployment commands remotely via SSH (pass DynamoDB table so Flask uses it on EC2)
ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" << REMOTE_DEPLOY
    set -e
    export DYNAMODB_PRODUCTS_TABLE="$DYNAMODB_PRODUCTS_TABLE"
    export AWS_REGION="$AWS_REGION"

    PACKAGE_NAME="product_catalogue.zip"
    DEPLOY_DIR="/opt/product_catalogue"

    echo "=========================================="
    echo "EXTRACTING PACKAGE ON EC2"
    echo "=========================================="

    # Create deployment directory
    sudo mkdir -p "\$DEPLOY_DIR"
    sudo chown ec2-user:ec2-user "\$DEPLOY_DIR"

    # Extract package
    cd /tmp
    if [ ! -f "\$PACKAGE_NAME" ]; then
        echo "Error: Package not found at /tmp/\$PACKAGE_NAME"
        exit 1
    fi

    echo "Extracting package to \$DEPLOY_DIR..."
    sudo unzip -o "\$PACKAGE_NAME" -d "\$DEPLOY_DIR"
    echo "✓ Package extracted"

    echo ""
    echo "=========================================="
    echo "RUNNING DEPLOYMENT SCRIPT"
    echo "=========================================="

    # Run deployment script (with DynamoDB env vars so it writes Flask env file)
    cd "\$DEPLOY_DIR"
    sudo -E ./deploy.sh
REMOTE_DEPLOY

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "DEPLOYMENT COMPLETE"
    echo "=========================================="
    echo "Service URL: http://$EC2_HOST:8000"
    echo ""
else
    echo ""
    echo "✗ Remote deployment failed"
    exit 1
fi
