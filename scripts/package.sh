#!/bin/bash
# Package the application for deployment
# This script only builds and packages the application locally - no EC2 interaction
# Use deploy_remote.sh to copy and deploy to EC2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/deploy"
PACKAGE_NAME="product_catalogue.zip"

echo "=========================================="
echo "PACKAGING APPLICATION"
echo "=========================================="

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
# Files are packaged locally in the deploy directory
# deploy_remote.sh will copy this package to EC2

echo ""
echo "=========================================="
echo "PACKAGING FILES FOR DEPLOYMENT"
echo "=========================================="
echo "Local staging directory: $OUTPUT_DIR"
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

# Copy runtime setup files (systemd service, etc.)
echo "Packaging runtime setup files..."
mkdir -p "$OUTPUT_DIR/runtime_setup"
cp -r "$SCRIPT_DIR/runtime_setup"/* "$OUTPUT_DIR/runtime_setup/" 2>/dev/null || echo "  → Note: Runtime setup directory not found or empty"
echo "  → Runtime setup files packaged (will be at /opt/product_catalogue/runtime_setup/ on EC2)"

# Copy seed script (runs on EC2 after deploy to seed DynamoDB)
echo "Packaging DynamoDB seed script..."
mkdir -p "$OUTPUT_DIR/scripts"
cp "$SCRIPT_DIR/seed_dynamodb.sh" "$OUTPUT_DIR/scripts/seed_dynamodb.sh"
chmod +x "$OUTPUT_DIR/scripts/seed_dynamodb.sh"
echo "  → Seed script packaged (will run on EC2)"

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
echo "=========================================="
echo "PACKAGING COMPLETE"
echo "=========================================="
echo "Package location: $OUTPUT_DIR/$PACKAGE_NAME"
echo ""
echo "Next step: Run ./scripts/deploy_remote.sh to copy and deploy to EC2"
echo ""
