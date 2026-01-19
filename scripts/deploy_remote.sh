#!/bin/bash
# Remote deployment script - runs deployment on EC2 instance via SSH
# This script is called after package.sh copies the archive to EC2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
PACKAGE_NAME="product_catalogue.zip"
EC2_USER="ec2-user"

echo "=========================================="
echo "REMOTE DEPLOYMENT TO EC2"
echo "=========================================="

# Get EC2 instance details from Terraform output
cd "$INFRASTRUCTURE_DIR"
EC2_PUBLIC_IP=$(terraform output -raw ec2_instance_public_ip 2>/dev/null || echo "")
EC2_PUBLIC_DNS=$(terraform output -raw ec2_instance_public_dns 2>/dev/null || echo "")
KEY_PAIR=$(terraform output -raw ec2_key_pair 2>/dev/null || echo "vockey")

if [ -z "$EC2_PUBLIC_IP" ] && [ -z "$EC2_PUBLIC_DNS" ]; then
    echo "Error: Could not retrieve EC2 instance details from Terraform output."
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

# Wait for SSH to be available
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

echo ""
echo "Deploying to EC2 instance..."
echo ""

# Run deployment commands remotely via SSH
ssh -i "$SSH_KEY" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "$EC2_USER@$EC2_HOST" << 'REMOTE_DEPLOY'
    set -e
    
    PACKAGE_NAME="product_catalogue.zip"
    DEPLOY_DIR="/opt/product_catalogue"
    
    echo "=========================================="
    echo "EXTRACTING PACKAGE ON EC2"
    echo "=========================================="
    
    # Create deployment directory
    sudo mkdir -p "$DEPLOY_DIR"
    sudo chown ec2-user:ec2-user "$DEPLOY_DIR"
    
    # Extract package
    cd /tmp
    if [ ! -f "$PACKAGE_NAME" ]; then
        echo "Error: Package not found at /tmp/$PACKAGE_NAME"
        exit 1
    fi
    
    echo "Extracting package to $DEPLOY_DIR..."
    sudo unzip -o "$PACKAGE_NAME" -d "$DEPLOY_DIR"
    echo "✓ Package extracted"
    
    echo ""
    echo "=========================================="
    echo "RUNNING DEPLOYMENT SCRIPT"
    echo "=========================================="
    
    # Run deployment script
    cd "$DEPLOY_DIR"
    sudo ./deploy.sh
    
    echo ""
    echo "=========================================="
    echo "DEPLOYMENT COMPLETE"
    echo "=========================================="
REMOTE_DEPLOY

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Remote deployment completed successfully!"
    echo ""
    echo "Application should be running at:"
    echo "  Flask API: http://$EC2_HOST:8000"
    echo "  React App: http://$EC2_HOST:3000"
else
    echo ""
    echo "✗ Remote deployment failed"
    exit 1
fi
