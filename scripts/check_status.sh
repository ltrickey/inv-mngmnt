#!/bin/bash
# Script to check the status of the Inventory API ECS Fargate service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="${INFRASTRUCTURE_DIR:-$PROJECT_ROOT/infrastructure}"

echo "=========================================="
echo "CHECKING INVENTORY API STATUS"
echo "=========================================="

AWS_REGION=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw aws_region 2>/dev/null || echo "us-east-1")
NAME_PREFIX=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw name_prefix 2>/dev/null || echo "")
INVENTORY_API_URL=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw inventory_api_url 2>/dev/null || echo "")

if [ -z "$NAME_PREFIX" ]; then
    echo "Error: Could not retrieve name_prefix from Terraform output."
    echo "Make sure Terraform has been applied."
    exit 1
fi

ECS_CLUSTER="${NAME_PREFIX}-inventory-api"
ECS_SERVICE="${NAME_PREFIX}-inventory-api"

echo "ECS Cluster: $ECS_CLUSTER"
echo "ECS Service: $ECS_SERVICE"
echo ""

echo "=========================================="
echo "ECS SERVICE STATUS"
echo "=========================================="
aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].{status:status,desiredCount:desiredCount,runningCount:runningCount,pendingCount:pendingCount}' \
    --output table || echo "Could not describe ECS service"

echo ""
echo "=========================================="
echo "RECENT TASK EVENTS"
echo "=========================================="
aws ecs describe-services \
    --cluster "$ECS_CLUSTER" \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].events[0:5].[createdAt,message]' \
    --output table || echo "Could not retrieve service events"

echo ""
echo "=========================================="
echo "HEALTH CHECK (via internal NLB — only reachable from within the VPC)"
echo "=========================================="
if [ -n "$INVENTORY_API_URL" ]; then
    echo "Inventory API URL: $INVENTORY_API_URL"
    echo "Health endpoint:   $INVENTORY_API_URL/health"
    echo "(Run this curl from an ECS task or an instance inside the VPC — not from your laptop)"
else
    echo "No inventory_api_url output found."
fi
echo ""
