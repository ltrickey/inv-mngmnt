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
EC2_PUBLIC_DNS=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw inventory_api_public_dns 2>/dev/null || echo "")
KEY_PAIR=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw ec2_key_pair 2>/dev/null || echo "vockey")

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

# Optionally restart Inventory API on EC2 to pick up any changes
if [ -n "$EC2_PUBLIC_DNS" ]; then
    echo ""
    read -p "Restart Inventory API service on EC2? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
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
            exit 1
        fi
        
        echo "Restarting Inventory API service..."
        ssh -i "$SSH_KEY" \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            ec2-user@"$EC2_PUBLIC_DNS" \
            "sudo systemctl restart inventory_api"
        
        if [ $? -eq 0 ]; then
            echo "✓ Inventory API service restarted"
            echo ""
            echo "Inventory API URL: http://$EC2_PUBLIC_DNS:9000"
        else
            echo "✗ Failed to restart Inventory API service"
        fi
    fi
fi

echo ""
echo "=========================================="
echo "DONE"
echo "=========================================="
