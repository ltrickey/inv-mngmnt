#!/bin/bash
# Package the inventory API for deployment
# This script only builds and packages the application locally - no EC2 interaction
# Use deploy_inventory_api_remote.sh to copy and deploy to EC2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/deploy/inventory_api"
PACKAGE_NAME="inventory_api.zip"

echo "=========================================="
echo "PACKAGING INVENTORY API"
echo "=========================================="

# ============================================
# PACKAGE FILES FOR DEPLOYMENT
# ============================================
# Files are packaged locally in the deploy directory
# deploy_inventory_api_remote.sh will copy this package to EC2

echo ""
echo "=========================================="
echo "PACKAGING FILES FOR DEPLOYMENT"
echo "=========================================="
echo "Local staging directory: $OUTPUT_DIR"
echo ""

# Create output directory (local staging area)
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Copy inventory API files
# These will be deployed to: /opt/inventory_api/
echo "Packaging inventory API files..."
cp -r "$PROJECT_ROOT/inventory_api"/* "$OUTPUT_DIR/"
# Remove any virtual environment if it exists (will be created on EC2)
rm -rf "$OUTPUT_DIR/.venv"
rm -rf "$OUTPUT_DIR/__pycache__"
rm -rf "$OUTPUT_DIR/*.pyc"
# Remove .env file (will be created on EC2 with production settings)
rm -f "$OUTPUT_DIR/.env"
# Remove tests directory — not needed on EC2
rm -rf "$OUTPUT_DIR/tests"
echo "  → Inventory API files packaged (will be at /opt/inventory_api/ on EC2)"

# Copy deployment script (standalone script to run on EC2)
echo "Packaging deployment script..."
cp "$SCRIPT_DIR/deploy_inventory_api.sh" "$OUTPUT_DIR/deploy.sh"
chmod +x "$OUTPUT_DIR/deploy.sh"
echo "  → Deployment script packaged (will be at /opt/inventory_api/deploy.sh on EC2)"

# Copy systemd service file
echo "Packaging systemd service file..."
mkdir -p "$OUTPUT_DIR/runtime_setup"
cp "$SCRIPT_DIR/runtime_setup/inventory_api.service" "$OUTPUT_DIR/runtime_setup/inventory_api.service"
echo "  → Systemd service file packaged (will be at /opt/inventory_api/runtime_setup/ on EC2)"

# ============================================
# CREATE DEPLOYMENT ARCHIVE
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
echo "=========================================="
echo "PACKAGING COMPLETE"
echo "=========================================="
echo "Package location: $OUTPUT_DIR/$PACKAGE_NAME"
echo ""
echo "Next step: Run ./scripts/deploy_inventory_api_remote.sh to copy and deploy to EC2"
echo ""
