# Inventory API - AWS Deployment Guide

Quick reference for deploying the Inventory API with API Gateway and EC2.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Internet                                  │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ HTTPS (with x-api-key header)
                       ▼
            ┌──────────────────────┐
            │   AWS API Gateway    │  ← API Key validation
            │  (Regional Endpoint) │  ← Rate limiting
            └──────────┬───────────┘  ← CORS support
                       │
                       │ VPC Link (private)
                       ▼
            ┌──────────────────────┐
            │   Network Load       │  ← TCP/9000
            │   Balancer (NLB)     │  ← Health checks
            └──────────┬───────────┘
                       │
                       │ Target Group
                       ▼
            ┌──────────────────────┐
            │   EC2 Instance       │  ← FastAPI app
            │   (inventory_api)    │  ← Port 9000
            └──────────┬───────────┘
                       │
                       │ AWS SDK (boto3)
                       ▼
            ┌──────────────────────┐
            │   DynamoDB Table     │  ← Inventory data
            │  (products_by_store) │
            └──────────────────────┘
```

## Quick Start

### 1. Deploy Infrastructure

```bash
cd infrastructure

# Initialize (first time only)
terraform init

# Review changes
terraform plan

# Deploy (VPC Link takes 5-10 minutes)
terraform apply
```

### 2. Get API Credentials

```bash
# Get API Gateway URL
terraform output api_gateway_url

# Get API key (sensitive - save securely)
terraform output -raw api_key_value
```

### 3. Test Deployment

```bash
API_URL=$(terraform output -raw api_gateway_url)
API_KEY=$(terraform output -raw api_key_value)

# Test health endpoint
curl -H "x-api-key: $API_KEY" "$API_URL/health"

# Test stock check
curl -H "x-api-key: $API_KEY" \
  "$API_URL/api/inventory/store1/12345?quantity=10"
```

## Local Development

### Start Services

```bash
cd inventory_api

# Start both backend (port 8000) and mock gateway (port 8001)
./start_local.sh
```

### Test Locally

```bash
# Set API key
export API_KEY="test-api-key-12345"

# Check stock
curl -H "x-api-key: $API_KEY" \
  "http://localhost:8001/api/inventory/store1/12345?quantity=10"

# Get price
curl -H "x-api-key: $API_KEY" \
  "http://localhost:8001/api/inventory/store1/12345/price"

# Deduct single
curl -X PATCH -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5}' \
  "http://localhost:8001/api/inventory/store1/12345"

# Deduct batch
curl -X PATCH -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"barcode": "12345", "quantity": 2}]}' \
  "http://localhost:8001/api/inventory/store1"
```

## API Endpoints

All endpoints require `x-api-key` header.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/inventory/{store_id}/{barcode}?quantity=N` | Check stock availability |
| `GET` | `/api/inventory/{store_id}/{barcode}/price` | Get price with sales |
| `PATCH` | `/api/inventory/{store_id}/{barcode}` | Deduct single item |
| `PATCH` | `/api/inventory/{store_id}` | Deduct batch (atomic) |

## Key Features

✅ **API Key Authentication** - Required for all endpoints  
✅ **Rate Limiting** - 100 req/s steady, 200 burst, 10K/day  
✅ **VPC Link** - Secure private connection to EC2  
✅ **Health Checks** - NLB monitors EC2 health  
✅ **CloudWatch Logs** - Request/response logging  
✅ **X-Ray Tracing** - Performance monitoring  
✅ **CORS Support** - Cross-origin requests enabled  
✅ **Atomic Batch Operations** - All-or-nothing updates  

## Files Created

### Infrastructure (Terraform)
- `infrastructure/api_gateway.tf` - Complete API Gateway config
- `infrastructure/modules/api_gateway_cors/` - CORS module
- `infrastructure/variables.tf` - Configuration variables
- `infrastructure/security.tf` - Security group rules (updated)

### Application
- `inventory_api/mock_api_gateway.py` - Local mock gateway
- `inventory_api/start_local.sh` - Dev server startup script
- `inventory_api/test_mock_gateway.py` - Gateway tests

### Documentation
- `inventory_api/API_GATEWAY_SETUP.md` - Detailed setup guide
- `inventory_api/DEPLOYMENT_GUIDE.md` - This file
- `changelog/CHANGELOG_API_GATEWAY_SETUP.md` - Complete changelog

## Testing

```bash
cd inventory_api

# Run all tests (68 tests)
pytest -v

# Run gateway tests only
pytest test_mock_gateway.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

## Terraform Outputs

```bash
# View all outputs
terraform output

# Specific outputs
terraform output api_gateway_url
terraform output api_key_id
terraform output -raw api_key_value  # Sensitive
terraform output vpc_link_id
```

## Configuration Variables

Located in `infrastructure/variables.tf`:

```hcl
# Rate limiting
api_quota_limit   = 10000  # requests/day
api_rate_limit    = 100    # requests/second
api_burst_limit   = 200    # concurrent requests

# Logging
log_retention_days = 7     # CloudWatch log retention
```

## Troubleshooting

### API Key Issues
```bash
# Verify key is enabled
aws apigateway get-api-key --api-key YOUR_KEY_ID --include-value
```

### VPC Link Status
```bash
# Check VPC Link (should be AVAILABLE)
aws apigateway get-vpc-link --vpc-link-id YOUR_VPC_LINK_ID
```

### EC2 Health
```bash
# Check NLB target health
aws elbv2 describe-target-health \
  --target-group-arn YOUR_TG_ARN
```

### Logs
```bash
# View API Gateway logs
aws logs tail /aws/apigateway/YOUR_PREFIX-inventory-api --follow

# View errors only
aws logs filter-pattern '/aws/apigateway/YOUR_PREFIX-inventory-api' \
  --filter-pattern '{ $.status >= 400 }'
```

## Cost Estimate

| Service | Monthly Cost (1M requests) |
|---------|---------------------------|
| API Gateway | $3.50 |
| VPC Link | $18.25 |
| Data Transfer | $0.90 |
| CloudWatch | $0.50 |
| **Total** | **~$23/month** |

*Plus EC2 and DynamoDB costs from existing infrastructure.*

## Production Checklist

Before production deployment:

- [ ] Change API key to secure value
- [ ] Document API key distribution process
- [ ] Set up CloudWatch alarms for errors
- [ ] Configure appropriate rate limits
- [ ] Enable AWS WAF (optional DDoS protection)
- [ ] Set up API key rotation policy
- [ ] Test all endpoints with production data
- [ ] Configure custom domain (optional)
- [ ] Set up monitoring dashboard
- [ ] Document API for consumers

## Support Resources

- **Detailed Setup**: See `API_GATEWAY_SETUP.md`
- **Changelog**: See `changelog/CHANGELOG_API_GATEWAY_SETUP.md`
- **API Reference**: See `API_REFERENCE.md`
- **Backend Docs**: http://localhost:8000/docs (local)
- **Gateway Info**: http://localhost:8001/ (local mock)

## Next Steps

1. **Deploy**: Run `terraform apply` in `infrastructure/`
2. **Test**: Use curl commands above with your API key
3. **Monitor**: Check CloudWatch for logs and metrics
4. **Scale**: Adjust rate limits as needed
5. **Distribute**: Share API key with authorized consumers

---

**Version:** 1.0.0  
**Last Updated:** February 13, 2026  
**Status:** ✅ Ready for Deployment
