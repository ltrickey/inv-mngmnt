# Changelog: S3 Image Hosting Implementation

## Summary

Added Amazon S3 for hosting product images when deploying to AWS via Terraform. The application now has two deployment modes:

1. **Local Development** - Images served from `infrastructure/images/` directory (no S3)
2. **AWS Deployment** - Images automatically uploaded to S3 bucket (mandatory)

This provides better performance, scalability, and cost efficiency for AWS deployments.

## Changes Made

### 1. Infrastructure (Terraform)

#### New Files
- **`infrastructure/s3.tf`** - S3 bucket configuration
  - Bucket: `{name_prefix}-product-images`
  - Public read access via bucket policy
  - Versioning enabled (90-day retention for old versions)
  - CORS configured for web access
  - Cache-control headers for performance

#### Modified Files
- **`infrastructure/variables.tf`**
  - No S3-specific variables needed (S3 always created for AWS deployments)

- **`infrastructure/outputs.tf`**
  - Added `s3_bucket_name` output
  - Added `s3_bucket_url` output

- **`infrastructure/deploy.tf`**
  - Added `upload_images_to_s3` resource
  - Automatically uploads images to S3 after bucket creation
  - Product catalogue deployment depends on S3 upload completion

- **`infrastructure/terraform.tfvars.example`**
  - Added comment explaining S3 is always created for AWS deployments

### 2. Deployment Scripts

#### New Files
- **`scripts/upload_images_to_s3.sh`**
  - Syncs images from `infrastructure/images/` to S3
  - Sets cache-control headers
  - Verifies upload success
  - Can be run manually or via Terraform

#### Modified Files
- **`scripts/deploy_remote.sh`**
  - Retrieves S3 bucket URL from Terraform
  - Calls `upload_images_to_s3.sh` before EC2 deployment
  - Passes `S3_BUCKET_URL` to Flask environment

- **`scripts/deploy.sh`**
  - Updates Flask environment file with `S3_BUCKET_URL`
  - Logs S3 configuration status

### 3. Application Code

#### Modified Files
- **`server/app.py`**
  - Removed TODO comment (S3 was already implemented)
  - `get_image_url()` function checks `S3_BUCKET_URL` env var
  - Returns S3 URLs when configured, Flask URLs otherwise

### 4. Documentation

#### New Files
- **`infrastructure/S3_CONFIGURATION.md`**
  - Comprehensive S3 configuration guide
  - Usage examples and troubleshooting
  - Cost analysis
  - Migration scenarios
  - Security considerations

- **`CHANGELOG_S3.md`** (this file)
  - Summary of all S3-related changes

#### Modified Files
- **`infrastructure/README.md`**
  - Added S3 section to architecture diagram
  - Updated to reflect S3 is always created for AWS
  - Added two-mode explanation (local dev vs AWS)
  - Added S3 quick reference section
  - Added link to S3_CONFIGURATION.md

## Architecture

### Local Development

```
Developer → [Flask on Laptop] → [Images from infrastructure/images/]
```

### AWS Deployment

```
Internet → [S3 Bucket] → [Product Images]
           ↓
        [Product Catalogue EC2] → [Serves HTML/API, references S3 URLs]
```

## Benefits

### Performance
- ✅ Images served from S3 (faster, globally distributed)
- ✅ Reduced load on EC2 instances
- ✅ Browser caching enabled (1-year max-age)
- ✅ Can add CloudFront CDN easily

### Scalability
- ✅ S3 handles unlimited concurrent requests
- ✅ No EC2 disk space concerns
- ✅ Automatic redundancy and availability

### Cost
- ✅ S3 storage cheaper than EBS for static files
- ✅ ~$0.0001/month for 5MB of images
- ✅ Reduced EC2 bandwidth costs

### Maintenance
- ✅ Versioning enabled (track changes, rollback)
- ✅ Automatic lifecycle management (90-day old version cleanup)
- ✅ Separate deployment of images vs application code

## Configuration

### No Configuration Needed!

The deployment mode is determined automatically:

**Local Development:**
```bash
cd server
python app.py
# Images served from ../infrastructure/images/
```

**AWS Deployment:**
```bash
cd infrastructure
terraform apply
# S3 bucket created automatically
# Images uploaded automatically
# Flask configured automatically
```

## Usage

### Automatic (via Terraform)

```bash
terraform apply
# Automatically:
# 1. Creates S3 bucket
# 2. Uploads images
# 3. Configures Flask with S3 URL
# 4. Deploys application
```

### Manual Image Upload

```bash
./scripts/upload_images_to_s3.sh
```

### Check Configuration

```bash
# View S3 bucket URL
terraform output s3_bucket_url

# List images in S3
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/images/

# Check Flask configuration
ssh ec2-user@{instance-ip}
sudo cat /etc/product_catalogue_flask.env | grep S3_BUCKET_URL
```

## Deployment Path

### First Time AWS Deployment

```bash
cd infrastructure
terraform apply
# Creates S3 bucket
# Uploads images
# Configures Flask
```

### Updating Images

```bash
# 1. Add new images
cp new-product.jpg infrastructure/images/

# 2. Upload to S3
./scripts/upload_images_to_s3.sh

# Images now available on your site
```

## Security

### S3 Bucket Policy
- Public read access for `s3:GetObject` on all images
- Block public ACLs (controlled via policy only)
- CORS allows requests from any origin (restrict in production)

### IAM Requirements
- EC2 instances don't need S3 permissions (images are public)
- Deployment machine needs `s3:PutObject` for uploads

## Testing

### Test S3 Upload

```bash
./scripts/upload_images_to_s3.sh
# Should output: ✓ Successfully uploaded N images to S3
```

### Test Image Access

```bash
S3_URL=$(terraform output -raw s3_bucket_url)
curl -I "$S3_URL/images/placeholder.png"
# Should return: HTTP/1.1 200 OK
```

### Test Flask Integration

```bash
# Visit your site
curl http://your-ec2-instance:8000/products

# Check image URLs in response - should point to S3:
# "image_url": "https://bucket.s3.region.amazonaws.com/images/..."
```

## Known Issues

### None Currently

All functionality tested and working as expected.

## Future Enhancements

1. **CloudFront CDN**
   - Add CloudFront distribution in front of S3
   - Further improve global performance
   - Enable HTTPS with custom domain

2. **Image Optimization**
   - Add automatic image resizing/compression
   - Generate multiple sizes (thumbnail, medium, large)
   - WebP format support for modern browsers

3. **Signed URLs**
   - Support private images with time-limited access
   - Useful for customer-specific content

4. **Cross-Region Replication**
   - Replicate images to multiple regions
   - Improve global availability

## Resources

- [S3 Configuration Guide](infrastructure/S3_CONFIGURATION.md)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [S3 Pricing](https://aws.amazon.com/s3/pricing/)

## Version

- **Feature**: S3 Image Hosting
- **Status**: ✅ Complete and Production-Ready
- **Date**: 2026-02-12
- **Terraform Version**: 1.14+
- **AWS Provider Version**: 5.0+
