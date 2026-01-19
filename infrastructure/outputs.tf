output "ec2_instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.product_catalogue.id
}

output "ec2_instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.product_catalogue.public_ip
}

output "ec2_instance_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.product_catalogue.public_dns
}

/* output "s3_bucket_name" {
  description = "Name of the S3 bucket for build artifacts"
  value       = aws_s3_bucket.build_artifacts.id
} */


output "service_url" {
  description = "URL to access the product catalogue via the flask app hosting react's index.html"
  value       = "http://${aws_instance.product_catalogue.public_dns}:8000"
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "ec2_key_pair" {
  description = "EC2 key pair name for SSH access"
  value       = var.ec2_key_pair
}