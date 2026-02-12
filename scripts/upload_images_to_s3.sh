#!/bin/bash
# Upload product images to S3 bucket
# This script is called during deployment to sync images to S3

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="${INFRASTRUCTURE_DIR:-$PROJECT_ROOT/infrastructure}"
IMAGES_DIR="$PROJECT_ROOT/infrastructure/images"

echo "=========================================="
echo "UPLOADING IMAGES TO S3"
echo "=========================================="

# Get S3 bucket name from Terraform output
if [ ! -d "$INFRASTRUCTURE_DIR" ]; then
    echo "Error: Infrastructure directory not found: $INFRASTRUCTURE_DIR"
    exit 1
fi

echo "Retrieving S3 bucket name from Terraform output..."
S3_BUCKET=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw s3_bucket_name 2>/dev/null || echo "")
AWS_REGION=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw aws_region 2>/dev/null || echo "us-east-1")

if [ -z "$S3_BUCKET" ]; then
    echo "Error: Could not retrieve S3 bucket name from Terraform output"
    echo "Make sure Terraform has been applied and S3 bucket is created"
    exit 1
fi

echo "S3 Bucket: $S3_BUCKET"
echo "AWS Region: $AWS_REGION"
echo "Images Directory: $IMAGES_DIR"
echo ""

# Check if images directory exists
if [ ! -d "$IMAGES_DIR" ]; then
    echo "Error: Images directory not found: $IMAGES_DIR"
    exit 1
fi

# Count images
IMAGE_COUNT=$(find "$IMAGES_DIR" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.gif" -o -name "*.webp" \) | wc -l | tr -d ' ')
echo "Found $IMAGE_COUNT image files to upload"
echo ""

# Upload images to S3
echo "Uploading images to S3..."
echo "Target: s3://$S3_BUCKET/images/"
echo ""

# Use AWS CLI to sync images
# --delete: Remove files in S3 that don't exist locally (optional)
# --acl public-read: Make images publicly accessible (alternative to bucket policy)
# --cache-control: Set cache headers for better performance

aws s3 sync "$IMAGES_DIR" "s3://$S3_BUCKET/images/" \
    --region "$AWS_REGION" \
    --cache-control "max-age=31536000, public" \
    --exclude "*" \
    --include "*.jpg" \
    --include "*.jpeg" \
    --include "*.png" \
    --include "*.gif" \
    --include "*.webp" \
    --no-progress

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Successfully uploaded $IMAGE_COUNT images to S3"
    echo ""
    echo "S3 Bucket: $S3_BUCKET (private - requires signed URLs)"
    echo "Images are not publicly accessible and can only be accessed via the Flask app"
    echo ""
else
    echo ""
    echo "✗ Failed to upload images to S3"
    exit 1
fi

# Verify upload
echo "Verifying upload..."
S3_IMAGE_COUNT=$(aws s3 ls "s3://$S3_BUCKET/images/" --region "$AWS_REGION" | wc -l | tr -d ' ')
echo "Images in S3: $S3_IMAGE_COUNT"

if [ "$S3_IMAGE_COUNT" -gt 0 ]; then
    echo "✓ Images successfully uploaded and verified"
else
    echo "⚠ Warning: No images found in S3 after upload"
fi

echo ""
echo "=========================================="
echo "UPLOAD COMPLETE"
echo "=========================================="
