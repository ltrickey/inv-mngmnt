# Automatically upload images to S3 after bucket is created
resource "terraform_data" "upload_images_to_s3" {
  depends_on = [
    aws_s3_bucket.product_images,
    aws_s3_bucket_policy.product_images
  ]

  triggers_replace = [
    aws_s3_bucket.product_images.id
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      PROJECT_ROOT="${abspath("${path.module}/..")}"
      INFRA_DIR="${abspath(path.module)}"
      cd "$PROJECT_ROOT"
      echo "=========================================="
      echo "TERRAFORM TRIGGERED S3 IMAGE UPLOAD"
      echo "=========================================="
      echo "Making upload script executable..."
      chmod +x scripts/upload_images_to_s3.sh
      echo ""
      echo "Uploading product images to S3..."
      INFRASTRUCTURE_DIR="$INFRA_DIR" ./scripts/upload_images_to_s3.sh
    EOT
  }
}

# Automatically build/push/deploy the Inventory API container after its ECS
# infrastructure is ready
resource "terraform_data" "deploy_inventory_api" {
  depends_on = [
    aws_ecr_repository.inventory_api,
    aws_ecs_cluster.inventory_api,
    aws_ecs_service.inventory_api,
  ]

  triggers_replace = [
    aws_ecr_repository.inventory_api.repository_url,
    aws_ecs_service.inventory_api.id,
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      PROJECT_ROOT="${abspath("${path.module}/..")}"
      cd "$PROJECT_ROOT"
      echo "Making deploy script executable..."
      chmod +x scripts/deploy_inventory_api.sh
      echo ""
      ECR_REPOSITORY_URL="${aws_ecr_repository.inventory_api.repository_url}" \
      AWS_REGION="${var.aws_region}" \
      ECS_CLUSTER="${aws_ecs_cluster.inventory_api.name}" \
      ECS_SERVICE="${aws_ecs_service.inventory_api.name}" \
      ./scripts/deploy_inventory_api.sh
    EOT
  }
}

# Automatically seed DynamoDB tables after they are created and deployments are complete
resource "terraform_data" "seed_dynamodb" {
  depends_on = [
    aws_dynamodb_table.products,
    aws_dynamodb_table.stores,
    aws_dynamodb_table.products_by_store,
    aws_dynamodb_table.categories,
    terraform_data.deploy_inventory_api
  ]

  triggers_replace = [
    aws_dynamodb_table.products.id,
    aws_dynamodb_table.stores.id,
    aws_dynamodb_table.products_by_store.id,
    aws_dynamodb_table.categories.id
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      PROJECT_ROOT="${abspath("${path.module}/..")}"
      INFRA_DIR="${abspath(path.module)}"
      cd "$PROJECT_ROOT"
      echo ""
      echo "=========================================="
      echo "TERRAFORM TRIGGERED DATABASE SEEDING"
      echo "=========================================="
      echo "Making seed script executable..."
      chmod +x scripts/seed_dynamodb.sh
      echo ""
      echo "Seeding DynamoDB tables with product data..."
      INFRASTRUCTURE_DIR="$INFRA_DIR" ./scripts/seed_dynamodb.sh
      echo ""
      echo "✓ Database seeding complete"
      echo "=========================================="
    EOT
  }
}

# Automatically deploy the Employee Site after all its infrastructure is ready
resource "terraform_data" "deploy_employee_site" {
  depends_on = [
    aws_ecr_repository.employee_bff,
    aws_ecs_cluster.employee,
    aws_ecs_service.employee_bff,
    aws_s3_bucket_policy.employee_site,
    aws_cognito_user_pool.employees,
    aws_cognito_user_pool_client.employee_site,
  ]

  triggers_replace = [
    aws_ecr_repository.employee_bff.repository_url,
    aws_ecs_service.employee_bff.id,
    aws_s3_bucket.employee_site.id,
    aws_cognito_user_pool.employees.id,
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      PROJECT_ROOT="${abspath("${path.module}/..")}"
      cd "$PROJECT_ROOT"
      echo "Making deploy script executable..."
      chmod +x scripts/deploy_employee_site.sh
      echo ""
      ECR_REPOSITORY_URL="${aws_ecr_repository.employee_bff.repository_url}" \
      AWS_REGION="${var.aws_region}" \
      COGNITO_USER_POOL_ID="${aws_cognito_user_pool.employees.id}" \
      COGNITO_APP_CLIENT_ID="${aws_cognito_user_pool_client.employee_site.id}" \
      EMPLOYEE_BFF_ALB_URL="http://${aws_lb.employee.dns_name}" \
      EMPLOYEE_SITE_BUCKET="${aws_s3_bucket.employee_site.id}" \
      ECS_CLUSTER="${aws_ecs_cluster.employee.name}" \
      ECS_SERVICE="${aws_ecs_service.employee_bff.name}" \
      ./scripts/deploy_employee_site.sh
    EOT
  }
}

# Automatically deploy the Customer Site after all its infrastructure is ready
resource "terraform_data" "deploy_customer_site" {
  depends_on = [
    aws_ecr_repository.customer_api,
    aws_ecs_cluster.customer,
    aws_ecs_service.customer_api,
    aws_s3_bucket_policy.customer_site,
    terraform_data.seed_dynamodb,
  ]

  triggers_replace = [
    aws_ecr_repository.customer_api.repository_url,
    aws_ecs_service.customer_api.id,
    aws_s3_bucket.customer_site.id,
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      PROJECT_ROOT="${abspath("${path.module}/..")}"
      cd "$PROJECT_ROOT"
      echo "Making deploy script executable..."
      chmod +x scripts/deploy_customer_site.sh
      echo ""
      ECR_REPOSITORY_URL="${aws_ecr_repository.customer_api.repository_url}" \
      AWS_REGION="${var.aws_region}" \
      CUSTOMER_API_ALB_URL="http://${aws_lb.customer.dns_name}" \
      CUSTOMER_SITE_BUCKET="${aws_s3_bucket.customer_site.id}" \
      ECS_CLUSTER="${aws_ecs_cluster.customer.name}" \
      ECS_SERVICE="${aws_ecs_service.customer_api.name}" \
      ./scripts/deploy_customer_site.sh
    EOT
  }
}
