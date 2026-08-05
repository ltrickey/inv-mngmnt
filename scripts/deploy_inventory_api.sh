#!/bin/bash
# Deploy the inventory API (FastAPI):
#   1. Build and push the Docker image to ECR
#   2. Force ECS to pick up the new image
#
# No frontend step here — this service has no SPA of its own.
#
# Required env vars (set by Terraform or manually):
#   ECR_REPOSITORY_URL, AWS_REGION, ECS_CLUSTER, ECS_SERVICE

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "=========================================="
echo "DEPLOYING INVENTORY API"
echo "=========================================="

# ============================================
# STEP 1: Build and push Docker image to ECR
# ============================================
echo ""
echo "Step 1: Building and pushing Inventory API Docker image..."
echo "  ECR: $ECR_REPOSITORY_URL"

# Use a temp Docker config dir to avoid macOS keychain conflicts
DOCKER_TEMP_CONFIG=$(mktemp -d)
echo '{"auths":{}}' > "$DOCKER_TEMP_CONFIG/config.json"
export DOCKER_CONFIG="$DOCKER_TEMP_CONFIG"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${ECR_REPOSITORY_URL%%/*}"

cd "$PROJECT_ROOT"
docker build --platform linux/amd64 -f inventory_api/Dockerfile -t inventory-api .
docker tag inventory-api:latest "$ECR_REPOSITORY_URL:latest"
docker push "$ECR_REPOSITORY_URL:latest"

echo "✓ Docker image pushed to ECR"

# ============================================
# STEP 2: Force ECS service to redeploy
# ============================================
echo ""
echo "Step 2: Updating ECS service..."

aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --no-cli-pager > /dev/null

echo "✓ ECS service update triggered (new task will pull latest image)"

echo ""
echo "=========================================="
echo "INVENTORY API DEPLOYMENT COMPLETE"
echo "=========================================="
