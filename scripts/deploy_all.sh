#!/bin/bash
# Deploys all three services:
#   1. Inventory API  — EC2 (FastAPI, port 9000)
#   2. Customer site  — ECR (Docker) + S3 (React frontend)
#   3. Employee site  — ECR (Docker) + S3 (React frontend)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "FULL DEPLOYMENT"
echo "=========================================="
echo "This script will deploy:"
echo "  1. Inventory API (FastAPI → EC2)"
echo "  2. Customer Site (Docker → ECR + React → S3)"
echo "  3. Employee Site (Docker → ECR + React → S3)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# ============================================
# STEP 1: DEPLOY INVENTORY API
# ============================================
echo ""
echo "=========================================="
echo "STEP 1: DEPLOYING INVENTORY API"
echo "=========================================="
"$SCRIPT_DIR/deploy_inventory_api_remote.sh"

# ============================================
# STEP 2: DEPLOY CUSTOMER SITE
# ============================================
echo ""
echo "=========================================="
echo "STEP 2: DEPLOYING CUSTOMER SITE"
echo "=========================================="
"$SCRIPT_DIR/deploy_customer_site.sh"

# ============================================
# STEP 3: DEPLOY EMPLOYEE SITE
# ============================================
echo ""
echo "=========================================="
echo "STEP 3: DEPLOYING EMPLOYEE SITE"
echo "=========================================="
"$SCRIPT_DIR/deploy_employee_site.sh"

# ============================================
# DEPLOYMENT COMPLETE
# ============================================
echo ""
echo "=========================================="
echo "ALL DEPLOYMENTS COMPLETE"
echo "=========================================="
echo ""
echo "  Inventory API: $(terraform -chdir="$SCRIPT_DIR/../infrastructure" output -raw inventory_api_public_dns 2>/dev/null | sed 's/^/http:\/\//'):9000"
echo "  Customer site: $(terraform -chdir="$SCRIPT_DIR/../infrastructure" output -raw customer_site_url 2>/dev/null)"
echo "  Employee site: $(terraform -chdir="$SCRIPT_DIR/../infrastructure" output -raw employee_site_url 2>/dev/null)"
echo ""
