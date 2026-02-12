# S3 Configuration for Product Images

## Overview

The application has **two deployment modes** for serving product images:

### 1. Local Development Mode

**When running on your laptop:**
- Images served from `infrastructure/images/` directory
- Flask serves images at `/images/` endpoint  
- No AWS infrastructure needed
- No S3 bucket created

**How it works:**
```python
# Flask checks for S3_BUCKET_URL environment variable
# If not set (local dev), serves from local directory
S3_BUCKET_URL = os.environ.get('S3_BUCKET_URL', None)  # None for local dev
```

### 2. AWS Deployment Mode (via Terraform)

**When deployed to AWS:**
- ✅ S3 bucket automatically created
- ✅ Images uploaded to S3 from `infrastructure/images/`
- ✅ Flask configured with `S3_BUCKET_URL` environment variable
- ✅ Better performance (CDN-ready)
- ✅ Reduced load on EC2 instances
- ✅ Scalable and reliable
- ✅ Automatic backups with versioning

**How it works:**
```bash
terraform apply
# 1. Creates S3 bucket: {name_prefix}-product-images
# 2. Uploads images to S3
# 3. Sets S3_BUCKET_URL in Flask environment
# 4. Flask serves image URLs pointing to S3
```

## No Configuration Needed!

The mode is determined automatically:

| Environment | S3 Created? | Image Source | Configuration |
|-------------|-------------|--------------|---------------|
| Local Dev | ❌ No | `infrastructure/images/` | None - just run Flask |
| AWS (Terraform) | ✅ Yes | S3 Bucket | Automatic via Terraform |

## S3 Bucket Configuration

The S3 bucket is configured with:

### Private Access with Signed URLs
- ✅ Bucket is **completely private** - no public access
- ✅ Images accessible only via time-limited signed URLs (1-hour expiration)
- ✅ All access controlled through Flask application
- ✅ Bucket policy allows access only from EC2 instances with LabRole
- ✅ Block all public access enabled

### Versioning
- Enabled to track image changes
- Old versions automatically deleted after 90 days

### CORS
- Allows `GET` and `HEAD` requests from any origin
- In production, restrict `allowed_origins` to your domain

### Caching
- Images uploaded with `cache-control: max-age=31536000` (1 year)
- Browser can cache signed URLs until they expire (1 hour)
- Signed URLs regenerated automatically when expired

## Image Upload Process

### When Deploying to AWS (Automatic)

`terraform apply` automatically:

```
1. Creates S3 bucket: {name_prefix}-product-images
2. Runs upload_images_to_s3.sh script
3. Syncs infrastructure/images/ → s3://bucket/images/
4. Sets S3_BUCKET_URL in Flask environment
5. Flask serves images from S3
```

### Manual Upload (Optional)

Upload images anytime after initial deployment:

```bash
./scripts/upload_images_to_s3.sh
```

This syncs all images from `infrastructure/images/` to S3.

### Local Development (No Upload)

When running locally:
```bash
cd server
python app.py
# Images served from ../infrastructure/images/
# No S3 upload needed
```

## Image URL Format

### AWS Deployment (S3 with Signed URLs)

Flask transforms image paths when `S3_BUCKET_NAME` is set:

```python
# DynamoDB stores: "infrastructure/images/4011-organic-bananas.jpg"
# Flask generates signed URL (valid for 1 hour):
# "https://bucket.s3.us-east-1.amazonaws.com/images/4011-organic-bananas.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Expires=3600&X-Amz-Signature=..."
```

**Signed URL Components:**
- Base URL: S3 object path
- Signature: Cryptographic signature proving validity
- Expiration: Timestamp when URL expires (1 hour from generation)
- Credentials: AWS credentials used to generate URL

### Local Development (No S3)

```python
# DynamoDB stores: "infrastructure/images/4011-organic-bananas.jpg"
# Flask returns: "/images/4011-organic-bananas.jpg"
# Served from: infrastructure/images/
```

## Adding New Images

### Step 1: Add Image File

```bash
cp my-new-product.jpg infrastructure/images/
```

### Step 2: Upload to S3

**Option A: Automatic (next deployment)**
```bash
terraform apply  # Re-uploads all images
```

**Option B: Manual Upload**
```bash
./scripts/upload_images_to_s3.sh
```

### Step 3: Update Product Data

Update the product in DynamoDB with the new image path:

```json
{
  "barcode": "1234567890123",
  "name": "My New Product",
  "image_url": "infrastructure/images/my-new-product.jpg"
}
```

Flask will automatically serve it from S3.

## Checking S3 Configuration

### View S3 Bucket URL

```bash
terraform output s3_bucket_url
```

### List Images in S3

```bash
S3_BUCKET=$(terraform output -raw s3_bucket_name)
aws s3 ls s3://$S3_BUCKET/images/
```

### Test Image Access

**Direct S3 access (should fail):**
```bash
S3_BUCKET=$(terraform output -raw s3_bucket_name)
curl -I "https://$S3_BUCKET.s3.us-east-1.amazonaws.com/images/placeholder.png"
```
Expected: `HTTP/1.1 403 Forbidden` ✅ (bucket is private)

**Via Flask (should work):**
```bash
# Get product with image
curl http://your-ec2:8000/products | jq '.[0].image_url'
# Returns signed URL with query parameters

# Test the signed URL
curl -I "$(curl -s http://your-ec2:8000/products | jq -r '.[0].image_url')"
```
Expected: `HTTP/1.1 200 OK` ✅

### Check Flask Configuration

SSH into EC2 and verify:

```bash
ssh -i ~/.ssh/vockey.pem ec2-user@{instance-ip}
sudo cat /etc/product_catalogue_flask.env | grep S3_BUCKET
# Should show:
# S3_BUCKET_NAME=product-catalogue-test-product-images
# S3_BUCKET_REGION=us-east-1
```

## Costs

### S3 Storage Costs (us-east-1)

Assuming ~100 images at ~50KB each = 5MB total:

- **Storage**: $0.023/GB/month → ~$0.0001/month
- **Requests**: $0.0004 per 1,000 GET requests
- **Data Transfer**: $0.09/GB after first 100GB/month (free tier)

**Total**: < $1/month for typical usage

### Cost Comparison

| Scenario | EC2 Only | EC2 + S3 |
|----------|----------|----------|
| EC2 Instance | t4g.micro (~$5/mo) | t4g.micro (~$5/mo) |
| Image Storage | Included in EBS | ~$0.0001/mo |
| Data Transfer | Higher (from EC2) | Lower (from S3) |
| Performance | Slower | Faster |
| **Total** | ~$5/mo | ~$5/mo |

S3 is essentially free for image hosting at this scale while providing better performance!

## Troubleshooting

### Error: "Error uploading images to S3"

**Check AWS credentials:**
```bash
aws sts get-caller-identity
```

**Check S3 bucket exists:**
```bash
aws s3 ls | grep product-images
```

**Check permissions:**
The IAM role needs `s3:PutObject` permission

### Images Not Loading on Website

**Check Flask configuration:**
```bash
ssh ec2-user@{instance-ip}
sudo cat /etc/product_catalogue_flask.env
# Should show: S3_BUCKET_URL=https://...
```

**Check browser console:**
- Open browser DevTools → Network tab
- Look for 403/404 errors on image requests
- Verify URLs are pointing to S3, not `/images/`

**Check S3 bucket policy:**
```bash
S3_BUCKET=$(terraform output -raw s3_bucket_name)
aws s3api get-bucket-policy --bucket $S3_BUCKET
```

Should allow public `GetObject`

### Images Out of Sync

Re-upload all images:

```bash
./scripts/upload_images_to_s3.sh
```

### S3 Bucket Already Exists Error

```
Error: Error creating S3 bucket: BucketAlreadyExists
```

This means a bucket with that name already exists (either yours or someone else's - S3 bucket names are globally unique).

**Solution 1:** Change project name or environment
```hcl
# In terraform.tfvars
project_name = "product-catalogue-unique-name"
# or
environment = "prod"  # creates prod-specific bucket name
```

**Solution 2:** Delete existing bucket (if it's yours)
```bash
aws s3 rb s3://product-catalogue-test-product-images --force
```

**Solution 3:** Use your AWS account ID in the name
```hcl
# In terraform.tfvars
project_name = "product-catalogue-${your-account-id}"
```

## Best Practices

### 1. S3 is Automatic for AWS
When you deploy with Terraform, S3 is automatically used - no configuration needed!

### 2. Optimize Images Before Upload
- Use JPEG for photos (smaller file size)
- Use PNG for graphics with transparency
- Compress images (e.g., with ImageMagick)
- Resize to appropriate dimensions

Example:
```bash
# Resize and compress
mogrify -resize 800x800 -quality 85 infrastructure/images/*.jpg
```

### 3. Use CloudFront (Optional)
For global distribution, add CloudFront CDN in front of S3:

```hcl
# Add to s3.tf
resource "aws_cloudfront_distribution" "images" {
  # CloudFront configuration
}
```

### 4. Monitor Costs
Set up billing alerts:

```bash
aws budgets create-budget \
  --budget BudgetName=S3Budget,BudgetLimit={Amount=5,Unit=USD}
```

### 5. Backup Images
S3 versioning is enabled, but for critical images:

```bash
# Backup to local
aws s3 sync s3://bucket-name/images/ ./backups/images/

# Or cross-region replication
# Configure in s3.tf
```

## Deployment Scenarios

### First Time Deployment

```bash
cd infrastructure
terraform init
terraform apply
# S3 bucket created automatically
# Images uploaded automatically
# Flask configured automatically
```

### Local Development → AWS Deployment

```bash
# 1. Develop locally (images from infrastructure/images/)
cd server
python app.py

# 2. Deploy to AWS (images automatically moved to S3)
cd ../infrastructure
terraform apply
```

### Re-deploying After Adding Images

```bash
# 1. Add new images to infrastructure/images/
cp new-product.jpg infrastructure/images/

# 2. Upload to S3
./scripts/upload_images_to_s3.sh

# 3. Update DynamoDB with new image references
# Flask will automatically serve new images from S3
```

## Security Considerations

### Private Bucket with Signed URLs

Current configuration: **Private with Signed URLs** ✅

**How it works:**
1. S3 bucket is completely private (no public access)
2. Flask generates signed URLs using boto3
3. Signed URLs are valid for 1 hour
4. After expiration, Flask generates new URLs automatically

**Security benefits:**
- ✅ No direct access to images
- ✅ Time-limited URLs (1-hour expiration)
- ✅ Prevents hot-linking to other sites
- ✅ All access goes through your application
- ✅ Can log/audit all image access

**URL expiration:**
```python
# Change expiration time in server/app.py
ExpiresIn=3600  # 1 hour (default)
ExpiresIn=900   # 15 minutes (more secure)
ExpiresIn=86400 # 24 hours (more caching)
```

### Restrict CORS Origins

In production, restrict to your domain:

```hcl
# s3.tf
cors_rule {
  allowed_origins = ["https://yourdomain.com"]
  # instead of ["*"]
}
```

## Quick Reference

| Task | Command |
|------|---------|
| Task | Command |
|------|---------|
| Deploy to AWS (creates S3) | `terraform apply` |
| Upload images to S3 | `./scripts/upload_images_to_s3.sh` |
| View S3 bucket name | `terraform output s3_bucket_name` |
| List images in S3 | `aws s3 ls s3://$(terraform output -raw s3_bucket_name)/images/` |
| Download from S3 | `aws s3 cp s3://bucket/images/file.jpg ./` |
| Delete bucket | `aws s3 rb s3://bucket --force` |
| Run locally (no S3) | `cd server && python app.py` |
