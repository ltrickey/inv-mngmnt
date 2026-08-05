#!/bin/bash
# Deploy the customer site:
#   1. Build and push the Customer API Docker image to ECR
#   2. Build the React frontend with production env vars and upload to S3
#   3. Force ECS to pick up the new image
#
# Required env vars (set by Terraform or manually):
#   ECR_REPOSITORY_URL, AWS_REGION,
#   CUSTOMER_API_ALB_URL, CUSTOMER_SITE_BUCKET,
#   ECS_CLUSTER, ECS_SERVICE

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "=========================================="
echo "DEPLOYING CUSTOMER SITE"
echo "=========================================="

# ============================================
# STEP 1: Build and push Docker image to ECR
# ============================================
echo ""
echo "Step 1: Building and pushing Customer API Docker image..."
echo "  ECR: $ECR_REPOSITORY_URL"

# Use a temp Docker config dir to avoid macOS keychain conflicts
DOCKER_TEMP_CONFIG=$(mktemp -d)
echo '{"auths":{}}' > "$DOCKER_TEMP_CONFIG/config.json"
export DOCKER_CONFIG="$DOCKER_TEMP_CONFIG"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${ECR_REPOSITORY_URL%%/*}"

cd "$PROJECT_ROOT"
docker build --platform linux/amd64 -f customer_site/server/Dockerfile -t customer-api .
docker tag customer-api:latest "$ECR_REPOSITORY_URL:latest"
docker push "$ECR_REPOSITORY_URL:latest"

echo "✓ Docker image pushed to ECR"

# ============================================
# STEP 2: Build React frontend and upload to S3
# ============================================
echo ""
echo "Step 2: Building and uploading React frontend..."
echo "  S3 bucket: $CUSTOMER_SITE_BUCKET"
echo "  API URL:   $CUSTOMER_API_ALB_URL"

cd "$PROJECT_ROOT/customer_site/site"

if [ ! -d "node_modules" ]; then
    echo "  Installing npm dependencies..."
    npm install
fi

VITE_API_BASE_URL="$CUSTOMER_API_ALB_URL" \
npm run build

aws s3 sync dist/ "s3://$CUSTOMER_SITE_BUCKET" --delete --region "$AWS_REGION"

echo "✓ React frontend uploaded to S3"

# ============================================
# STEP 3: Force ECS service to redeploy
# ============================================
echo ""
echo "Step 3: Updating ECS service..."

aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --no-cli-pager > /dev/null

echo "✓ ECS service update triggered (new task will pull latest image)"

echo ""
echo "=========================================="
echo "CUSTOMER SITE DEPLOYMENT COMPLETE"
echo "=========================================="
echo "  API:       $CUSTOMER_API_ALB_URL"
echo "  Frontend:  http://$CUSTOMER_SITE_BUCKET.s3-website-${AWS_REGION}.amazonaws.com"
echo "=========================================="
