#!/bin/bash
# Convenience script to package and deploy both the Product Catalogue and Inventory API
# This script orchestrates the full deployment process

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "FULL DEPLOYMENT"
echo "=========================================="
echo "This script will package and deploy:"
echo "  1. Product Catalogue (Flask + React)"
echo "  2. Inventory API (FastAPI)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# ============================================
# STEP 1: PACKAGE PRODUCT CATALOGUE
# ============================================
echo ""
echo "=========================================="
echo "STEP 1: PACKAGING PRODUCT CATALOGUE"
echo "=========================================="
"$SCRIPT_DIR/package.sh"

if [ $? -ne 0 ]; then
    echo "✗ Failed to package Product Catalogue"
    exit 1
fi

# ============================================
# STEP 2: PACKAGE INVENTORY API
# ============================================
echo ""
echo "=========================================="
echo "STEP 2: PACKAGING INVENTORY API"
echo "=========================================="
"$SCRIPT_DIR/package_inventory_api.sh"

if [ $? -ne 0 ]; then
    echo "✗ Failed to package Inventory API"
    exit 1
fi

# ============================================
# STEP 3: DEPLOY PRODUCT CATALOGUE
# ============================================
echo ""
echo "=========================================="
echo "STEP 3: DEPLOYING PRODUCT CATALOGUE"
echo "=========================================="
"$SCRIPT_DIR/deploy_remote.sh"

if [ $? -ne 0 ]; then
    echo "✗ Failed to deploy Product Catalogue"
    exit 1
fi

# ============================================
# STEP 4: DEPLOY INVENTORY API
# ============================================
echo ""
echo "=========================================="
echo "STEP 4: DEPLOYING INVENTORY API"
echo "=========================================="
"$SCRIPT_DIR/deploy_inventory_api_remote.sh"

if [ $? -ne 0 ]; then
    echo "✗ Failed to deploy Inventory API"
    exit 1
fi

# ============================================
# DEPLOYMENT COMPLETE
# ============================================
echo ""
echo "=========================================="
echo "ALL DEPLOYMENTS COMPLETE"
echo "=========================================="
echo ""
echo "✓ Product Catalogue deployed successfully"
echo "✓ Inventory API deployed successfully"
echo ""
echo "To view deployment details:"
echo "  terraform -chdir=infrastructure output"
echo ""
