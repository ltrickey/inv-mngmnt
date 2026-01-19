# Automatically deploy application after EC2 instance is created
# This uses local-exec to run the deployment scripts from your local machine
resource "null_resource" "deploy_app" {
  depends_on = [aws_instance.product_catalogue]

  triggers = {
    instance_id = aws_instance.product_catalogue.id
    # Re-deploy if instance changes
    instance_public_ip = aws_instance.product_catalogue.public_ip
  }

  provisioner "local-exec" {
    command = <<-EOT
      cd ${path.module}/..
      echo "=========================================="
      echo "TERRAFORM TRIGGERED DEPLOYMENT"
      echo "=========================================="
      echo "Making scripts executable..."
      chmod +x scripts/package.sh scripts/deploy_remote.sh scripts/deploy.sh
      echo "Building and packaging application..."
      ./scripts/package.sh --skip-deploy
      echo ""
      echo "Deploying to EC2 instance..."
      ./scripts/deploy_remote.sh
    EOT
  }
}
