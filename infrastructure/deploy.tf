# Automatically deploy Product Catalogue after EC2 instance is created
# This uses local-exec to run the deployment scripts from your local machine
# terraform_data is the recommended built-in resource (replaces null_resource in Terraform v1.14+)
resource "terraform_data" "deploy_product_catalogue" {
  depends_on = [aws_instance.product_catalogue]

  triggers_replace = [
    aws_instance.product_catalogue.id,
    aws_instance.product_catalogue.public_ip
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      PROJECT_ROOT="${abspath("${path.module}/..")}"
      INFRA_DIR="${abspath(path.module)}"
      cd "$PROJECT_ROOT"
      echo "=========================================="
      echo "TERRAFORM TRIGGERED DEPLOYMENT - PRODUCT CATALOGUE"
      echo "=========================================="
      echo "Making scripts executable..."
      chmod +x scripts/package.sh scripts/deploy_remote.sh scripts/deploy.sh scripts/seed_dynamodb.sh
      echo ""
      echo "Building and packaging application..."
      ./scripts/package.sh
      echo ""
      echo "Deploying to EC2 instance (DynamoDB will be seeded on EC2)..."
      INFRASTRUCTURE_DIR="$INFRA_DIR" ./scripts/deploy_remote.sh
    EOT
  }
}

# Automatically deploy Inventory API after EC2 instance is created
resource "terraform_data" "deploy_inventory_api" {
  depends_on = [aws_instance.inventory_api]

  triggers_replace = [
    aws_instance.inventory_api.id,
    aws_instance.inventory_api.public_ip
  ]

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      PROJECT_ROOT="${abspath("${path.module}/..")}"
      INFRA_DIR="${abspath(path.module)}"
      cd "$PROJECT_ROOT"
      echo "=========================================="
      echo "TERRAFORM TRIGGERED DEPLOYMENT - INVENTORY API"
      echo "=========================================="
      echo "Making scripts executable..."
      chmod +x scripts/package_inventory_api.sh scripts/deploy_inventory_api_remote.sh scripts/deploy_inventory_api.sh
      echo ""
      echo "Packaging Inventory API..."
      ./scripts/package_inventory_api.sh
      echo ""
      echo "Deploying Inventory API to EC2 instance..."
      INFRASTRUCTURE_DIR="$INFRA_DIR" ./scripts/deploy_inventory_api_remote.sh
    EOT
  }
}
