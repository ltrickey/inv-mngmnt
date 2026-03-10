#!/bin/bash
# Deploy the employee internal site:
#   1. Build and push the BFF Docker image to ECR
#   2. Build the React frontend with production env vars and upload to S3
#   3. Force ECS to pick up the new image
#
# Required env vars (set by Terraform or manually):
#   ECR_REPOSITORY_URL, AWS_REGION,
#   COGNITO_USER_POOL_ID, COGNITO_APP_CLIENT_ID,
#   EMPLOYEE_BFF_ALB_URL, EMPLOYEE_SITE_BUCKET,
#   ECS_CLUSTER, ECS_SERVICE

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "=========================================="
echo "DEPLOYING EMPLOYEE SITE"
echo "=========================================="

# ============================================
# STEP 1: Build and push Docker image to ECR
# ============================================
echo ""
echo "Step 1: Building and pushing BFF Docker image..."
echo "  ECR: $ECR_REPOSITORY_URL"

# Use a temp Docker config dir to avoid macOS keychain conflicts
DOCKER_TEMP_CONFIG=$(mktemp -d)
echo '{"auths":{}}' > "$DOCKER_TEMP_CONFIG/config.json"
export DOCKER_CONFIG="$DOCKER_TEMP_CONFIG"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${ECR_REPOSITORY_URL%%/*}"

cd "$PROJECT_ROOT/employee_site/server"
docker build --platform linux/amd64 -t employee-bff .
docker tag employee-bff:latest "$ECR_REPOSITORY_URL:latest"
docker push "$ECR_REPOSITORY_URL:latest"

echo "✓ Docker image pushed to ECR"

# ============================================
# STEP 2: Build React frontend and upload to S3
# ============================================
echo ""
echo "Step 2: Building and uploading React frontend..."
echo "  S3 bucket: $EMPLOYEE_SITE_BUCKET"
echo "  API URL:   $EMPLOYEE_BFF_ALB_URL"

cd "$PROJECT_ROOT/employee_site/site"

if [ ! -d "node_modules" ]; then
    echo "  Installing npm dependencies..."
    npm install
fi

VITE_COGNITO_USER_POOL_ID="$COGNITO_USER_POOL_ID" \
VITE_COGNITO_APP_CLIENT_ID="$COGNITO_APP_CLIENT_ID" \
VITE_API_BASE_URL="$EMPLOYEE_BFF_ALB_URL" \
npm run build

aws s3 sync dist/ "s3://$EMPLOYEE_SITE_BUCKET" --delete --region "$AWS_REGION"

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
echo "EMPLOYEE SITE DEPLOYMENT COMPLETE"
echo "=========================================="
echo "  BFF API:   $EMPLOYEE_BFF_ALB_URL"
echo "  Frontend:  http://$EMPLOYEE_SITE_BUCKET.s3-website-${AWS_REGION}.amazonaws.com"
echo "=========================================="
