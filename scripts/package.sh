#!/bin/bash
# Package the application for deployment to EC2

set -e

# Check for --skip-deploy flag
SKIP_DEPLOY=false
if [[ "$*" == *"--skip-deploy"* ]]; then
    SKIP_DEPLOY=true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
OUTPUT_DIR="$PROJECT_ROOT/deploy"
PACKAGE_NAME="product_catalogue.zip"

# Default EC2 username based on AMI type
# Amazon Linux: ec2-user
# Ubuntu: ubuntu
# Debian: admin
# For Amazon Linux 2023/AL2, use "ec2-user"
EC2_USER="ec2-user"

echo "Packaging application for deployment..."

# Check if infrastructure directory exists
if [ ! -d "$INFRASTRUCTURE_DIR" ]; then
    echo "Error: Infrastructure directory not found at $INFRASTRUCTURE_DIR"
    exit 1
fi

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

# Use DNS if available, otherwise use IP
EC2_HOST="${EC2_PUBLIC_DNS:-$EC2_PUBLIC_IP}"
echo "Target EC2 instance: $EC2_HOST"

# Determine SSH key path (common locations)
SSH_KEY=""
if [ -f "$HOME/.ssh/${KEY_PAIR}.pem" ]; then
    SSH_KEY="$HOME/.ssh/${KEY_PAIR}.pem"
elif [ -f "$HOME/.ssh/${KEY_PAIR}" ]; then
    SSH_KEY="$HOME/.ssh/${KEY_PAIR}"
elif [ -f "$INFRASTRUCTURE_DIR/${KEY_PAIR}.pem" ]; then
    SSH_KEY="$INFRASTRUCTURE_DIR/${KEY_PAIR}.pem"
else
    echo "Warning: Could not find SSH key for ${KEY_PAIR}.pem"
    echo "Please set SSH_KEY environment variable or ensure key is in ~/.ssh/${KEY_PAIR}.pem"
    read -p "Enter path to SSH key (or press Enter to continue without key check): " SSH_KEY
fi

# Build React application
echo "Building React application..."
cd "$PROJECT_ROOT/site"
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
fi
npm run build

if [ ! -d "dist" ]; then
    echo "Error: React build failed - dist directory not found"
    exit 1
fi

echo "React build completed successfully"

# ============================================
# STEP 2: PACKAGE FILES FOR DEPLOYMENT
# ============================================
# Files are packaged locally, then copied to EC2
# Final destination on EC2: /opt/product_catalogue/

echo ""
echo "=========================================="
echo "PACKAGING FILES FOR DEPLOYMENT"
echo "=========================================="
echo "Local staging directory: $OUTPUT_DIR"
echo "Final EC2 destination: /opt/product_catalogue/"
echo ""

# Create output directory (local staging area)
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Copy Flask server files
# These will be deployed to: /opt/product_catalogue/server/
echo "Packaging Flask server files..."
mkdir -p "$OUTPUT_DIR/server"
cp -r "$PROJECT_ROOT/server"/* "$OUTPUT_DIR/server/"
# Remove any virtual environment if it exists (will be created on EC2)
rm -rf "$OUTPUT_DIR/server/.venv"
rm -rf "$OUTPUT_DIR/server/__pycache__"
rm -rf "$OUTPUT_DIR/server/*.pyc"
echo "  → Flask files packaged (will be at /opt/product_catalogue/server/ on EC2)"

# Copy React build
# These will be deployed to: /opt/product_catalogue/site-dist/
echo "Packaging React build..."
cp -r "$PROJECT_ROOT/site/dist" "$OUTPUT_DIR/site-dist"
echo "  → React build packaged (will be at /opt/product_catalogue/site-dist/ on EC2)"

# Copy product images (if needed locally, otherwise they'll be in S3)
# These will be deployed to: /opt/product_catalogue/infrastructure/images/
echo "Packaging product images..."
mkdir -p "$OUTPUT_DIR/infrastructure/images"
cp -r "$PROJECT_ROOT/infrastructure/images"/* "$OUTPUT_DIR/infrastructure/images/" 2>/dev/null || echo "  → Note: Images directory not found or empty"
echo "  → Images packaged (will be at /opt/product_catalogue/infrastructure/images/ on EC2)"

# Copy deployment script (standalone script to run on EC2)
echo "Packaging deployment script..."
cp "$SCRIPT_DIR/deploy.sh" "$OUTPUT_DIR/deploy.sh"
chmod +x "$OUTPUT_DIR/deploy.sh"
echo "  → Deployment script packaged (will be at /opt/product_catalogue/deploy.sh on EC2)"

# ============================================
# STEP 3: CREATE DEPLOYMENT ARCHIVE
# ============================================
echo ""
echo "=========================================="
echo "CREATING DEPLOYMENT ARCHIVE"
echo "=========================================="
cd "$OUTPUT_DIR"
if command -v zip &> /dev/null; then
    zip -r "$PACKAGE_NAME" . -x "*.git*" "*.DS_Store" "*.swp" "*.swo"
else
    tar -czf "${PACKAGE_NAME%.zip}.tar.gz" . --exclude="*.git*" --exclude="*.DS_Store"
    PACKAGE_NAME="${PACKAGE_NAME%.zip}.tar.gz"
fi

echo "✓ Archive created: $OUTPUT_DIR/$PACKAGE_NAME"
echo ""

# ============================================
# STEP 4: COPY TO EC2 INSTANCE VIA SCP
# ============================================
echo ""
echo "=========================================="
echo "COPYING PACKAGE TO EC2 INSTANCE"
echo "=========================================="
echo "EC2 Instance: $EC2_HOST"
echo "EC2 User: $EC2_USER"
echo ""
echo "COPY DESTINATION ON EC2:"
echo "  Temporary location: /tmp/$PACKAGE_NAME"
echo "  (Will be extracted to: /opt/product_catalogue/)"
echo ""

if [ -n "$SSH_KEY" ] && [ -f "$SSH_KEY" ]; then
    echo "Using SSH key: $SSH_KEY"
    echo "Copying $PACKAGE_NAME to EC2 instance..."
    echo ""
    
    scp -i "$SSH_KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        "$OUTPUT_DIR/$PACKAGE_NAME" \
        "$EC2_USER@$EC2_HOST:/tmp/"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ Package successfully copied to EC2 instance!"
        echo ""
        echo "LOCATION ON EC2:"
        echo "  Package: /tmp/$PACKAGE_NAME"
        echo ""
        
        # Automatically deploy via SSH (unless --skip-deploy flag is set)
        if [ "$SKIP_DEPLOY" = false ]; then
            echo "=========================================="
            echo "AUTOMATIC DEPLOYMENT"
            echo "=========================================="
            echo "Running remote deployment script..."
            echo ""
            "$SCRIPT_DIR/deploy_remote.sh"
        else
            echo ""
            echo "Skipping automatic deployment (--skip-deploy flag set)"
            echo "Run ./scripts/deploy_remote.sh manually to deploy"
        fi
    else
        echo ""
        echo "✗ Failed to copy package to EC2 instance"
        echo "Package is ready locally at: $OUTPUT_DIR/$PACKAGE_NAME"
        exit 1
    fi
else
    echo "⚠ SSH key not found. Package is ready locally but not copied to EC2."
    echo ""
    echo "LOCAL PACKAGE LOCATION:"
    echo "  $OUTPUT_DIR/$PACKAGE_NAME"
    echo ""
    echo "To manually copy to EC2 instance, run:"
    echo "  scp -i <your-key.pem> $OUTPUT_DIR/$PACKAGE_NAME $EC2_USER@$EC2_HOST:/tmp/"
    echo ""
    echo "Then on EC2 instance:"
    echo "  1. Extract package:"
    echo "     sudo mkdir -p /opt/product_catalogue"
    echo "     cd /tmp"
    echo "     sudo unzip -o $PACKAGE_NAME -d /opt/product_catalogue"
    echo ""
    echo "  2. Run deployment script:"
    echo "     sudo /opt/product_catalogue/deploy.sh"
fi

echo ""
echo "Packaging complete!"
