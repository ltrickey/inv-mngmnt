#!/bin/bash
# Clean up AWS resources that exist but aren't tracked by Terraform
# Run this when terraform apply fails with "already exists" errors

set -e

echo "=========================================="
echo "CLEANING UP ORPHANED AWS RESOURCES"
echo "=========================================="
echo ""
echo "This will delete AWS resources that exist but aren't in Terraform state."
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

# Function to safely delete if resource exists
safe_delete() {
    local cmd="$1"
    local desc="$2"
    echo "→ $desc"
    if eval "$cmd" 2>/dev/null; then
        echo "  ✓ Deleted"
    else
        echo "  ⊘ Not found or already deleted"
    fi
}

echo ""
echo "Step 1: Deleting old API Gateway that blocks VPC Link cleanup..."
# The old API Gateway (1hs3idyf0i) must be deleted before the VPC Link
OLD_API_ID="1hs3idyf0i"
API_EXISTS=$(aws apigateway get-rest-api --rest-api-id "$OLD_API_ID" --query 'id' --output text 2>/dev/null || echo "")
if [ -n "$API_EXISTS" ] && [ "$API_EXISTS" != "None" ]; then
    echo "  → Deleting API Gateway: $OLD_API_ID"
    aws apigateway delete-rest-api --rest-api-id "$OLD_API_ID"
    echo "    ✓ Deleted"
    echo "  → Waiting for API Gateway cleanup (15 seconds)..."
    sleep 15
else
    echo "  ⊘ Old API Gateway not found (may have been deleted already)"
fi

echo ""
echo "Step 2: Finding and deleting VPC Links..."
# VPC Links must be deleted after API Gateway and before NLB
VPC_LINKS=$(aws apigateway get-vpc-links --query "items[?name=='product-catalogue-test-inventory-api-vpc-link' || contains(targetArns, 'pcat-test-inv-nlb')].id" --output text 2>/dev/null || echo "")
if [ -n "$VPC_LINKS" ]; then
    for VPC_LINK_ID in $VPC_LINKS; do
        echo "  → Deleting VPC Link: $VPC_LINK_ID"
        aws apigateway delete-vpc-link --vpc-link-id "$VPC_LINK_ID" || echo "    ⊘ Failed or already deleted"
        echo "    ✓ Deletion initiated"
    done
    echo "  → Waiting for VPC Link deletion to complete (60 seconds)..."
    sleep 60
else
    echo "  ⊘ No VPC Links found"
fi

echo ""
echo "Step 3: Deleting Network Load Balancer..."
NLB_ARN=$(aws elbv2 describe-load-balancers --names pcat-test-inv-nlb --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || echo "")
if [ -n "$NLB_ARN" ] && [ "$NLB_ARN" != "None" ]; then
    aws elbv2 delete-load-balancer --load-balancer-arn "$NLB_ARN"
    echo "  ✓ NLB deleted, waiting for it to finish..."
    sleep 30
else
    echo "  ⊘ NLB not found"
fi

echo ""
echo "Step 4: Deleting Target Group..."
TG_ARN=$(aws elbv2 describe-target-groups --names pcat-test-inv-tg --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null || echo "")
if [ -n "$TG_ARN" ] && [ "$TG_ARN" != "None" ]; then
    aws elbv2 delete-target-group --target-group-arn "$TG_ARN"
    echo "  ✓ Target Group deleted"
else
    echo "  ⊘ Target Group not found"
fi

echo ""
echo "Step 5: Deleting CloudWatch Log Group..."
safe_delete "aws logs delete-log-group --log-group-name /aws/apigateway/product-catalogue-test-inventory-api" "CloudWatch log group"

echo ""
echo "Step 6: Deleting DynamoDB Tables..."
echo "  (This may take a minute...)"
safe_delete "aws dynamodb delete-table --table-name product-catalogue-test-products" "  - products table"
safe_delete "aws dynamodb delete-table --table-name product-catalogue-test-stores" "  - stores table"
safe_delete "aws dynamodb delete-table --table-name product-catalogue-test-products_by_store" "  - products_by_store table"
safe_delete "aws dynamodb delete-table --table-name categories" "  - categories table"

echo ""
echo "Step 7: Emptying and deleting S3 bucket (with versioning)..."
BUCKET_NAME="product-catalogue-test-product-images"
BUCKET_EXISTS=$(aws s3api head-bucket --bucket "$BUCKET_NAME" 2>&1 || echo "NotFound")
if [[ "$BUCKET_EXISTS" != *"NotFound"* ]]; then
    echo "  → Deleting all object versions..."
    aws s3api delete-objects --bucket "$BUCKET_NAME" \
        --delete "$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}' --max-items 1000)" \
        2>/dev/null || echo "    ⊘ No versions to delete"
    
    echo "  → Deleting all delete markers..."
    aws s3api delete-objects --bucket "$BUCKET_NAME" \
        --delete "$(aws s3api list-object-versions --bucket "$BUCKET_NAME" --query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' --max-items 1000)" \
        2>/dev/null || echo "    ⊘ No delete markers"
    
    echo "  → Deleting bucket..."
    aws s3api delete-bucket --bucket "$BUCKET_NAME"
    echo "  ✓ S3 bucket deleted"
else
    echo "  ⊘ S3 bucket not found"
fi

echo ""
echo "Step 8: Checking for EC2 instances using the security groups..."
PC_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=product-catalogue-test-product-catalogue-sg --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
INV_SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values=product-catalogue-test-inventory-api-sg --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")

# Check for EC2 instances using these security groups
if [ -n "$PC_SG_ID" ] && [ "$PC_SG_ID" != "None" ]; then
    PC_INSTANCES=$(aws ec2 describe-instances --filters "Name=instance.group-id,Values=$PC_SG_ID" "Name=instance-state-name,Values=running,stopped,stopping,pending" --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null || echo "")
    if [ -n "$PC_INSTANCES" ]; then
        echo "  ⚠ Product catalogue security group has EC2 instances attached: $PC_INSTANCES"
        echo "    → These instances should be managed by Terraform"
        echo "    → Skipping security group deletion (Terraform will handle it)"
    fi
fi

if [ -n "$INV_SG_ID" ] && [ "$INV_SG_ID" != "None" ]; then
    INV_INSTANCES=$(aws ec2 describe-instances --filters "Name=instance.group-id,Values=$INV_SG_ID" "Name=instance-state-name,Values=running,stopped,stopping,pending" --query 'Reservations[].Instances[].InstanceId' --output text 2>/dev/null || echo "")
    if [ -n "$INV_INSTANCES" ]; then
        echo "  ⚠ Inventory API security group has EC2 instances attached: $INV_INSTANCES"
        echo "    → These instances should be managed by Terraform"
        echo "    → Skipping security group deletion (Terraform will handle it)"
    fi
fi

echo ""
echo "Step 9: Attempting to delete security groups (if no EC2 dependencies)..."
if [ -n "$PC_SG_ID" ] && [ "$PC_SG_ID" != "None" ] && [ -z "$PC_INSTANCES" ]; then
    aws ec2 delete-security-group --group-id "$PC_SG_ID" && echo "  ✓ Product catalogue security group deleted" || echo "  ⊘ Could not delete (may have dependencies)"
else
    echo "  ⊘ Product catalogue security group skipped or not found"
fi

if [ -n "$INV_SG_ID" ] && [ "$INV_SG_ID" != "None" ] && [ -z "$INV_INSTANCES" ]; then
    aws ec2 delete-security-group --group-id "$INV_SG_ID" && echo "  ✓ Inventory API security group deleted" || echo "  ⊘ Could not delete (may have dependencies)"
else
    echo "  ⊘ Inventory API security group skipped or not found"
fi

echo ""
echo "=========================================="
echo "CLEANUP COMPLETE"
echo "=========================================="
echo ""
echo "You can now run: terraform apply"
echo ""
