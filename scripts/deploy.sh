#!/bin/bash
# Deployment script to run on EC2 instance
# Can be run manually but is automatically run by Terraform when the infrastructure is deployed
# This script extracts the package and sets up the application

set -e

DEPLOY_DIR="/opt/product_catalogue"
PACKAGE_PATH="/tmp/product_catalogue.zip"
SERVICE_USER="ec2-user"

echo "=========================================="
echo "PRODUCT CATALOGUE DEPLOYMENT"
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

# Set up Flask server
echo ""
echo "Setting up Flask server..."
cd "$DEPLOY_DIR/server"

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

# Set up React app (if serving statically)
if [ -d "../site-dist" ]; then
    echo "✓ React build found at $DEPLOY_DIR/site-dist"
fi

# Create env file for Flask (DynamoDB table name and region when deploying from Terraform)
FLASK_ENV_FILE="/etc/product_catalogue_flask.env"
if [ -n "$DYNAMODB_PRODUCTS_TABLE" ]; then
  echo "Configuring Flask to use DynamoDB (table: $DYNAMODB_PRODUCTS_TABLE)"
  {
    echo "USE_DYNAMODB=1"
    echo "DYNAMODB_PRODUCTS_TABLE=$DYNAMODB_PRODUCTS_TABLE"
    [ -n "$AWS_REGION" ] && echo "AWS_REGION=$AWS_REGION"
  } | sudo tee "$FLASK_ENV_FILE" > /dev/null
else
  echo "USE_DYNAMODB=0" | sudo tee "$FLASK_ENV_FILE" > /dev/null
fi
echo "✓ Flask env file created at $FLASK_ENV_FILE"

# Set up systemd service for Flask
echo ""
echo "Setting up Flask service..."
SERVICE_FILE="$DEPLOY_DIR/runtime_setup/product_catalogue_flask.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Error: Service file not found at $SERVICE_FILE"
    exit 1
fi

sudo cp "$SERVICE_FILE" /etc/systemd/system/product_catalogue_flask.service
sudo systemctl daemon-reload
sudo systemctl enable product_catalogue_flask

# Terminate the previously running instance of the web server
echo "Stopping existing web server instance..."
if sudo systemctl is-active --quiet product_catalogue_flask; then
    sudo systemctl stop product_catalogue_flask
    echo "✓ Previous web server instance stopped"
else
    echo "  → No running instance found (this is normal for first deployment)"
fi

# Start a new instance using the newly deployed code
echo "Starting web server with newly deployed code..."
sudo systemctl start product_catalogue_flask

# Check service status
sleep 2
if sudo systemctl is-active --quiet product_catalogue_flask; then
    echo "✓ Flask service is running"
else
    echo "⚠ Warning: Flask service may not be running. Check status with:"
    echo "  sudo systemctl status product_catalogue_flask"
fi

# Verify service is enabled (will start on boot)
if sudo systemctl is-enabled --quiet product_catalogue_flask; then
    echo "✓ Flask service is enabled (will start automatically on boot)"
else
    echo "⚠ Warning: Flask service is not enabled. Enabling now..."
    sudo systemctl enable product_catalogue_flask
    echo "✓ Flask service enabled"
fi

echo ""
echo "✓ Deployment script completed successfully"
echo ""
