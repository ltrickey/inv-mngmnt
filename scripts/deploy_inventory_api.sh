#!/bin/bash
# Deployment script to run on EC2 instance for Inventory API
# Can be run manually but is automatically run by deploy_inventory_api_remote.sh
# This script extracts the package and sets up the application

set -e

DEPLOY_DIR="/opt/inventory_api"
PACKAGE_PATH="/tmp/inventory_api.zip"
SERVICE_USER="ec2-user"

echo "=========================================="
echo "INVENTORY API DEPLOYMENT"
echo "=========================================="
echo "Deployment directory: $DEPLOY_DIR"
echo "Package location: $PACKAGE_PATH"
echo ""

# Check if package exists
if [ ! -f "$PACKAGE_PATH" ]; then
    echo "Error: Package not found at $PACKAGE_PATH"
    echo "Please ensure the package has been copied to the EC2 instance first."
    exit 1
fi

# Create deployment directory
echo "Creating deployment directory..."
sudo mkdir -p "$DEPLOY_DIR"
sudo chown $SERVICE_USER:$SERVICE_USER "$DEPLOY_DIR"

# Extract package
echo "Extracting package..."
cd "$DEPLOY_DIR"
if [ -f "$PACKAGE_PATH" ]; then
    unzip -o "$PACKAGE_PATH"
    echo "✓ Package extracted"
else
    echo "Error: Package file not found"
    exit 1
fi

# Set up Inventory API
echo ""
echo "Setting up Inventory API..."
cd "$DEPLOY_DIR"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi

echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# Create env file for Inventory API (DynamoDB table name and region when deploying from Terraform)
API_ENV_FILE="/etc/inventory_api.env"
if [ -n "$DYNAMODB_PRODUCTS_TABLE" ]; then
  echo "Configuring Inventory API to use DynamoDB (table: $DYNAMODB_PRODUCTS_TABLE)"
  {
    echo "USE_DYNAMODB=1"
    echo "DYNAMODB_PRODUCTS_TABLE=$DYNAMODB_PRODUCTS_TABLE"
    echo "NAME_PREFIX=$NAME_PREFIX"
    [ -n "$AWS_REGION" ] && echo "AWS_REGION=$AWS_REGION"
  } | sudo tee "$API_ENV_FILE" > /dev/null
else
  echo "USE_DYNAMODB=0" | sudo tee "$API_ENV_FILE" > /dev/null
fi
echo "✓ Inventory API env file created at $API_ENV_FILE"

# Set up systemd service for Inventory API
echo ""
echo "Setting up Inventory API service..."
SERVICE_FILE="$DEPLOY_DIR/runtime_setup/inventory_api.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

sudo cp "$SERVICE_FILE" /etc/systemd/system/inventory_api.service
sudo systemctl daemon-reload
sudo systemctl enable inventory_api

# Terminate the previously running instance of the API
echo "Stopping existing Inventory API instance..."
if sudo systemctl is-active --quiet inventory_api; then
    sudo systemctl stop inventory_api
    echo "✓ Previous Inventory API instance stopped"
else
    echo "  → No running instance found (this is normal for first deployment)"
fi

# Start a new instance using the newly deployed code
echo "Starting Inventory API with newly deployed code..."
sudo systemctl start inventory_api

# Check service status
sleep 2
if sudo systemctl is-active --quiet inventory_api; then
    echo "✓ Inventory API service is running"
else
    echo "⚠ Warning: Inventory API service may not be running. Check status with:"
    echo "  sudo systemctl status inventory_api"
fi

# Verify service is enabled (will start on boot)
if sudo systemctl is-enabled --quiet inventory_api; then
    echo "✓ Inventory API service is enabled (will start automatically on boot)"
else
    echo "⚠ Warning: Inventory API service is not enabled. Enabling now..."
    sudo systemctl enable inventory_api
    echo "✓ Inventory API service enabled"
fi

echo ""
echo "✓ Deployment script completed successfully"
echo ""
