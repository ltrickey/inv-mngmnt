#!/bin/bash
# Imports pre-existing AWS resources into Terraform state after a state reset.
# Run this from the project root when "terraform apply" fails with "already exists" errors.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA="$SCRIPT_DIR/../infrastructure"

echo "=========================================="
echo "TERRAFORM IMPORT — existing resources"
echo "=========================================="
echo ""

# Import, but ignore "already managed" errors (resource already in state)
tf() { terraform -chdir="$INFRA" import "$@" 2>&1 | grep -v "^$" || true; }

# ── DynamoDB tables ────────────────────────────────────────────────────────────
echo "--- DynamoDB tables ---"
tf aws_dynamodb_table.products              product-catalogue-test-products
tf aws_dynamodb_table.stores               product-catalogue-test-stores
tf aws_dynamodb_table.products_by_store    product-catalogue-test-products_by_store
tf aws_dynamodb_table.sales_events         product-catalogue-test-sales_events
tf aws_dynamodb_table.report_schedules     product-catalogue-test-report_schedules
tf aws_dynamodb_table.report_results       product-catalogue-test-report_results
tf aws_dynamodb_table.categories           categories

# ── S3 buckets ────────────────────────────────────────────────────────────────
echo ""
echo "--- S3 buckets ---"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
tf aws_s3_bucket.customer_site   "product-catalogue-test-customer-site-${ACCOUNT_ID}"
tf aws_s3_bucket.employee_site   "product-catalogue-test-employee-site-${ACCOUNT_ID}"
tf aws_s3_bucket.product_images  "product-catalogue-test-product-images-${ACCOUNT_ID}"
tf aws_s3_bucket.reports         "product-catalogue-test-reports-${ACCOUNT_ID}"

# ── ECR repositories ──────────────────────────────────────────────────────────
echo ""
echo "--- ECR repositories ---"
tf aws_ecr_repository.customer_api  product-catalogue-test-customer-api
tf aws_ecr_repository.employee_bff  product-catalogue-test-employee-bff

# ── CloudWatch log groups ─────────────────────────────────────────────────────
echo ""
echo "--- CloudWatch log groups ---"
tf aws_cloudwatch_log_group.api_gateway   /aws/apigateway/product-catalogue-test-inventory-api
tf aws_cloudwatch_log_group.customer_api  /ecs/product-catalogue-test-customer-api
tf aws_cloudwatch_log_group.employee_bff  /ecs/product-catalogue-test-employee-bff

# ── EventBridge schedule group ────────────────────────────────────────────────
echo ""
echo "--- EventBridge schedule group ---"
tf aws_scheduler_schedule_group.reports product-catalogue-test-reports

# ── Security groups (need IDs) ────────────────────────────────────────────────
echo ""
echo "--- Security groups ---"
SG_CUSTOMER=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=product-catalogue-test-customer-alb-sg" \
  --query 'SecurityGroups[0].GroupId' --output text)
SG_EMPLOYEE=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=product-catalogue-test-employee-alb-sg" \
  --query 'SecurityGroups[0].GroupId' --output text)
echo "  customer ALB SG: $SG_CUSTOMER"
echo "  employee ALB SG: $SG_EMPLOYEE"
tf aws_security_group.customer_alb "$SG_CUSTOMER"
tf aws_security_group.employee_alb "$SG_EMPLOYEE"

# ── NLB (inventory API) ───────────────────────────────────────────────────────
echo ""
echo "--- Load balancers ---"
LB_ARN=$(aws elbv2 describe-load-balancers \
  --names pcat-test-inv-nlb \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)
echo "  inventory NLB: $LB_ARN"
tf aws_lb.inventory_api "$LB_ARN"

# ── Target groups ─────────────────────────────────────────────────────────────
echo ""
echo "--- Target groups ---"
TG_INV=$(aws elbv2 describe-target-groups --names pcat-test-inv-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)
TG_CUST=$(aws elbv2 describe-target-groups --names pcat-test-cust-api-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)
TG_EMP=$(aws elbv2 describe-target-groups --names pcat-test-emp-bff-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)
echo "  inventory TG:  $TG_INV"
echo "  customer TG:   $TG_CUST"
echo "  employee TG:   $TG_EMP"
tf aws_lb_target_group.inventory_api "$TG_INV"
tf aws_lb_target_group.customer_api  "$TG_CUST"
tf aws_lb_target_group.employee_bff  "$TG_EMP"

# ── ALBs (customer + employee) ────────────────────────────────────────────────
echo ""
echo "--- ALBs ---"
ALB_CUST=$(aws elbv2 describe-load-balancers --names pcat-test-cust-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || echo "")
ALB_EMP=$(aws elbv2 describe-load-balancers --names pcat-test-emp-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null || echo "")
if [ -n "$ALB_CUST" ] && [ "$ALB_CUST" != "None" ]; then
  echo "  customer ALB: $ALB_CUST"
  tf aws_lb.customer "$ALB_CUST"
fi
if [ -n "$ALB_EMP" ] && [ "$ALB_EMP" != "None" ]; then
  echo "  employee ALB: $ALB_EMP"
  tf aws_lb.employee "$ALB_EMP"
fi

# ── ECS security groups ───────────────────────────────────────────────────────
echo ""
echo "--- ECS security groups ---"
SG_CUST_ECS=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=product-catalogue-test-customer-ecs-sg" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
SG_EMP_ECS=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=product-catalogue-test-employee-ecs-sg" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
if [ -n "$SG_CUST_ECS" ] && [ "$SG_CUST_ECS" != "None" ]; then
  echo "  customer ECS SG: $SG_CUST_ECS"
  tf aws_security_group.customer_ecs "$SG_CUST_ECS"
fi
if [ -n "$SG_EMP_ECS" ] && [ "$SG_EMP_ECS" != "None" ]; then
  echo "  employee ECS SG: $SG_EMP_ECS"
  tf aws_security_group.employee_ecs "$SG_EMP_ECS"
fi

# ── Lambda ────────────────────────────────────────────────────────────────────
echo ""
echo "--- Lambda ---"
tf aws_lambda_function.report_generator product-catalogue-test-report-generator

# ── API Gateway VPC Link ──────────────────────────────────────────────────────
# The NLB is already associated with a VPC endpoint service, so find & import
# the existing VPC link rather than creating a new one.
echo ""
echo "--- API Gateway VPC Link ---"
# Import the AVAILABLE VPC link (skip FAILED ones)
VPC_LINK_ID=$(aws apigateway get-vpc-links \
  --query "items[?name=='product-catalogue-test-inventory-api-vpc-link' && status=='AVAILABLE'].id | [0]" \
  --output text 2>/dev/null || echo "")
if [ -n "$VPC_LINK_ID" ] && [ "$VPC_LINK_ID" != "None" ]; then
  echo "  VPC link (AVAILABLE): $VPC_LINK_ID"
  # Delete any FAILED VPC links with the same name first
  aws apigateway get-vpc-links \
    --query "items[?name=='product-catalogue-test-inventory-api-vpc-link' && status=='FAILED'].id" \
    --output text 2>/dev/null | tr '\t' '\n' | grep -v '^$' | while read -r fid; do
      echo "  Deleting FAILED VPC link: $fid"
      aws apigateway delete-vpc-link --vpc-link-id "$fid" 2>/dev/null || true
  done
  # Remove any tainted state entry before importing
  terraform -chdir="$INFRA" state rm aws_api_gateway_vpc_link.inventory_api 2>/dev/null || true
  tf aws_api_gateway_vpc_link.inventory_api "$VPC_LINK_ID"
else
  echo "  WARNING: no AVAILABLE VPC link found — run: aws apigateway get-vpc-links"
fi

# ── Lambda permission ─────────────────────────────────────────────────────────
echo ""
echo "--- Lambda permission ---"
tf aws_lambda_permission.allow_eventbridge_scheduler \
  "product-catalogue-test-report-generator/AllowEventBridgeScheduler"

# ── Inventory API security group ──────────────────────────────────────────────
echo ""
echo "--- Inventory API security group ---"
SG_INV=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=product-catalogue-test-inventory-api-sg" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")
if [ -n "$SG_INV" ] && [ "$SG_INV" != "None" ]; then
  echo "  inventory API SG: $SG_INV"
  tf aws_security_group.inventory_api "$SG_INV"
fi

# ── ECS services ──────────────────────────────────────────────────────────────
echo ""
echo "--- ECS services ---"
tf aws_ecs_service.customer_api \
  "product-catalogue-test-customer/product-catalogue-test-customer-api"
tf aws_ecs_service.employee_bff \
  "product-catalogue-test-employee/product-catalogue-test-employee-bff"

echo ""
echo "=========================================="
echo "Import complete. Run: terraform -chdir=infrastructure apply"
echo "=========================================="
