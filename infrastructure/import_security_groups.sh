#!/bin/bash
# Import existing security groups into Terraform state (one-time operation)

set -e

echo "=========================================="
echo "IMPORTING SECURITY GROUPS"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# Get security group IDs
echo "→ Finding security groups in AWS..."
PC_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=product-catalogue-test-product-catalogue-sg --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
INV_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=product-catalogue-test-inventory-api-sg --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")

if [ -z "$PC_SG_ID" ] || [ "$PC_SG_ID" = "None" ]; then
    echo "  ⊘ Product catalogue security group not found - nothing to import"
else
    echo "  ✓ Found product catalogue security group: $PC_SG_ID"
    echo "→ Importing aws_security_group.product_catalogue..."
    terraform import aws_security_group.product_catalogue "$PC_SG_ID" || echo "  ⊘ Already imported or failed"
fi

if [ -z "$INV_SG_ID" ] || [ "$INV_SG_ID" = "None" ]; then
    echo "  ⊘ Inventory API security group not found - nothing to import"
else
    echo "  ✓ Found inventory API security group: $INV_SG_ID"
    echo "→ Importing aws_security_group.inventory_api..."
    terraform import aws_security_group.inventory_api "$INV_SG_ID" || echo "  ⊘ Already imported or failed"
fi

echo ""
echo "=========================================="
echo "IMPORT COMPLETE"
echo "=========================================="
echo ""
echo "You can now run: terraform apply"
echo ""
