#!/bin/bash
# Check DynamoDB table status and re-seed if needed
# Run this script if products are not showing up

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="${INFRASTRUCTURE_DIR:-$PROJECT_ROOT/infrastructure}"

echo "=========================================="
echo "CHECKING DYNAMODB TABLES"
echo "=========================================="

# Get configuration from Terraform
NAME_PREFIX=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw name_prefix 2>/dev/null || echo "")
AWS_REGION=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw aws_region 2>/dev/null || echo "us-east-1")

if [ -z "$NAME_PREFIX" ]; then
    echo "Error: Could not get NAME_PREFIX from Terraform"
    exit 1
fi

PRODUCTS_TABLE="${NAME_PREFIX}-products"
STORES_TABLE="${NAME_PREFIX}-stores"
PRODUCTS_BY_STORE_TABLE="${NAME_PREFIX}-products_by_store"

echo "Region: $AWS_REGION"
echo "Products table: $PRODUCTS_TABLE"
echo "Stores table: $STORES_TABLE"
echo "Products by store table: $PRODUCTS_BY_STORE_TABLE"
echo ""

# Check if tables exist and count items
echo "Checking table item counts..."
echo ""

check_table_count() {
    local table_name=$1
    echo -n "  $table_name: "
    count=$(aws dynamodb scan \
        --table-name "$table_name" \
        --select "COUNT" \
        --region "$AWS_REGION" \
        --output text \
        --query 'Count' 2>/dev/null || echo "ERROR")
    
    if [ "$count" = "ERROR" ]; then
        echo "❌ Table not found or inaccessible"
        return 1
    else
        echo "$count items"
        return 0
    fi
}

NEEDS_SEED=0

if ! check_table_count "$PRODUCTS_TABLE"; then
    NEEDS_SEED=1
fi

if ! check_table_count "$STORES_TABLE"; then
    NEEDS_SEED=1
fi

if ! check_table_count "$PRODUCTS_BY_STORE_TABLE"; then
    NEEDS_SEED=1
fi

echo ""

if [ $NEEDS_SEED -eq 1 ]; then
    echo "⚠️  Some tables are empty or missing"
    echo ""
    read -p "Would you like to seed the DynamoDB tables? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Seeding DynamoDB tables..."
        SEED_DATA_DIR="$PROJECT_ROOT/seed_data" \
        DYNAMODB_PRODUCTS_TABLE="$PRODUCTS_TABLE" \
        AWS_REGION="$AWS_REGION" \
        "$SCRIPT_DIR/seed_dynamodb.sh"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✓ DynamoDB tables seeded successfully"
        else
            echo ""
            echo "✗ Failed to seed DynamoDB tables"
            exit 1
        fi
    fi
else
    echo "✓ All tables have data"
fi

# Optionally force a fresh ECS deployment to pick up any changes
if [ -n "$NAME_PREFIX" ]; then
    echo ""
    read -p "Force a new Inventory API ECS deployment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Triggering new ECS deployment..."
        aws ecs update-service \
            --cluster "${NAME_PREFIX}-inventory-api" \
            --service "${NAME_PREFIX}-inventory-api" \
            --force-new-deployment \
            --region "$AWS_REGION" \
            --no-cli-pager > /dev/null

        if [ $? -eq 0 ]; then
            echo "✓ Inventory API ECS deployment triggered"
        else
            echo "✗ Failed to trigger ECS deployment"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "DONE"
echo "=========================================="
