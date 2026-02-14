# API Gateway Setup and Local Testing

This guide covers deploying the Inventory API with AWS API Gateway and testing locally with a mock API Gateway.

## Architecture

```
┌─────────────────┐
│   API Gateway   │  ← External clients with API keys
│  (API Keys)     │
└────────┬────────┘
         │ VPC Link
         ▼
┌─────────────────┐
│  Network LB     │  ← Internal load balancer
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  EC2 Instance   │  ← FastAPI app on port 9000
│ (Inventory API) │
└─────────────────┘
```

## Terraform Resources Created

### API Gateway Components

1. **REST API Gateway** - Main API Gateway resource
2. **Resources** - URL path structure
   - `/api/inventory/{store_id}/{barcode}` - Stock check, price, single deduct
   - `/api/inventory/{store_id}/{barcode}/price` - Price endpoint
   - `/api/inventory/{store_id}` - Batch deduct
3. **Methods** - HTTP methods with API key requirement
4. **Integrations** - HTTP_PROXY connections to EC2 via VPC Link
5. **API Key** - Generated key for authentication
6. **Usage Plan** - Rate limiting and quotas
7. **Deployment & Stage** - Prod stage deployment

### Networking Components

1. **Network Load Balancer** - Routes traffic to EC2 instance
2. **Target Group** - EC2 instance on port 9000
3. **VPC Link** - Connects API Gateway to private NLB
4. **Security Group Rules** - Allows API Gateway traffic

### Monitoring

1. **CloudWatch Logs** - API Gateway request/response logs
2. **X-Ray Tracing** - Distributed tracing enabled

## Deployment

### Prerequisites

1. EC2 instance running inventory API on port 9000
2. DynamoDB tables configured
3. Security groups allowing traffic

### Deploy Infrastructure

```bash
cd infrastructure

# Initialize Terraform (if not already done)
terraform init

# Plan the changes
terraform plan

# Apply the configuration
terraform apply
```

### Get API Key

After deployment, retrieve the API key:

```bash
# Get API key value
terraform output -raw api_key_value

# Or view all API Gateway outputs
terraform output | grep api
```

**Save this key securely!** You'll need it for all API requests.

## Local Testing with Mock API Gateway

For local development, we provide a mock API Gateway that simulates AWS API Gateway's API key authentication.

### Quick Start

```bash
cd inventory_api

# Option 1: Start both backend and gateway
./start_local.sh

# Option 2: Start individually
./start_local.sh --backend-only   # Backend only on port 8000
./start_local.sh --gateway-only   # Gateway only on port 8001
```

### Manual Setup

```bash
# Terminal 1: Start the backend FastAPI app
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start the mock API Gateway
python mock_api_gateway.py
```

### Configuration

Set environment variables to customize:

```bash
# Change API key
export MOCK_API_KEY=my-custom-key

# Change backend URL
export BACKEND_URL=http://localhost:8000

# Change gateway port
export MOCK_PORT=8001

# Then start
python mock_api_gateway.py
```

## Testing API Endpoints

### With Mock Gateway (Local)

```bash
# Set API key
API_KEY="test-api-key-12345"

# 1. Check stock availability
curl -H "x-api-key: $API_KEY" \
  "http://localhost:8001/api/inventory/store1/12345?quantity=10"

# 2. Get product price
curl -H "x-api-key: $API_KEY" \
  "http://localhost:8001/api/inventory/store1/12345/price"

# 3. Deduct single item
curl -X PATCH \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5}' \
  "http://localhost:8001/api/inventory/store1/12345"

# 4. Deduct batch
curl -X PATCH \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"barcode": "12345", "quantity": 2},
      {"barcode": "67890", "quantity": 1}
    ]
  }' \
  "http://localhost:8001/api/inventory/store1"
```

### Without API Key (Should Fail)

```bash
# This will return 403 Forbidden
curl "http://localhost:8001/api/inventory/store1/12345?quantity=10"

# Response:
# {"message": "Forbidden"}
```

### With AWS API Gateway (Production)

```bash
# Get your API Gateway URL from Terraform
API_URL=$(cd infrastructure && terraform output -raw api_gateway_url)
API_KEY=$(cd infrastructure && terraform output -raw api_key_value)

# Make requests
curl -H "x-api-key: $API_KEY" \
  "$API_URL/api/inventory/store1/12345?quantity=10"
```

## API Endpoints

All endpoints require `x-api-key` header.

### 1. Check Stock Availability

```http
GET /api/inventory/{store_id}/{barcode}?quantity={min_quantity}
Headers: x-api-key: your-api-key
```

**Response:**
```json
{
  "store_id": "store1",
  "barcode": "12345",
  "available": true,
  "current_quantity": 100,
  "requested_quantity": 10
}
```

### 2. Get Price with Sales

```http
GET /api/inventory/{store_id}/{barcode}/price
Headers: x-api-key: your-api-key
```

**Response:**
```json
{
  "store_id": "store1",
  "barcode": "12345",
  "original_price": 19.99,
  "percent_off": 10,
  "final_price": 17.99
}
```

### 3. Deduct Single Item

```http
PATCH /api/inventory/{store_id}/{barcode}
Headers: 
  x-api-key: your-api-key
  Content-Type: application/json
Body: {"quantity": 5}
```

**Response:**
```json
{
  "success": true,
  "store_id": "store1",
  "barcode": "12345",
  "deducted_quantity": 5,
  "new_quantity": 95
}
```

### 4. Deduct Batch (Atomic)

```http
PATCH /api/inventory/{store_id}
Headers: 
  x-api-key: your-api-key
  Content-Type: application/json
Body: {
  "items": [
    {"barcode": "12345", "quantity": 2},
    {"barcode": "67890", "quantity": 1}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "store_id": "store1",
  "items_updated": 2,
  "items": [
    {"barcode": "12345", "deducted_quantity": 2, "new_quantity": 98},
    {"barcode": "67890", "deducted_quantity": 1, "new_quantity": 49}
  ]
}
```

## Rate Limiting

The API Gateway usage plan includes:

- **Daily Quota**: 10,000 requests per day (configurable)
- **Rate Limit**: 100 requests/second steady state (configurable)
- **Burst Limit**: 200 concurrent requests (configurable)

Configure in `infrastructure/variables.tf`:

```hcl
variable "api_quota_limit" {
  default = 10000  # requests per day
}

variable "api_rate_limit" {
  default = 100    # requests per second
}

variable "api_burst_limit" {
  default = 200    # concurrent requests
}
```

## Security Group Configuration

The EC2 instance security group allows:

1. **Traffic from Product Catalogue** - Port 9000 (existing)
2. **Traffic from VPC (API Gateway)** - Port 9000 (new)
3. **SSH Access** - Port 22 (management)

## Monitoring and Logging

### CloudWatch Logs

API Gateway logs are sent to CloudWatch:

```bash
# View logs
aws logs tail /aws/apigateway/your-prefix-inventory-api --follow

# Filter by status code
aws logs filter-pattern '/aws/apigateway/your-prefix-inventory-api' \
  --filter-pattern '{ $.status = 403 }'
```

### X-Ray Tracing

Distributed tracing is enabled. View traces in AWS X-Ray console to debug performance issues.

### Metrics

View API Gateway metrics in CloudWatch:
- Request count
- Latency (min, max, avg)
- 4xx and 5xx errors
- Integration latency

## Troubleshooting

### API Key Not Working

```bash
# Verify API key is enabled
aws apigateway get-api-key --api-key YOUR_KEY_ID --include-value

# Check usage plan association
aws apigateway get-usage-plan-keys --usage-plan-id YOUR_PLAN_ID
```

### 403 Forbidden Errors

- Verify `x-api-key` header is present
- Check API key is enabled
- Verify usage plan association
- Check if quota is exceeded

### 502 Bad Gateway Errors

- Verify EC2 instance is running
- Check FastAPI is listening on port 9000
- Verify NLB health checks are passing
- Check security group rules

### VPC Link Issues

```bash
# Check VPC Link status
aws apigateway get-vpc-link --vpc-link-id YOUR_VPC_LINK_ID

# Status should be "AVAILABLE"
```

### Health Check

```bash
# Check backend health directly
curl http://EC2_PRIVATE_IP:9000/health

# Through gateway
curl -H "x-api-key: $API_KEY" \
  "$API_GATEWAY_URL/health"
```

## Testing

### Unit Tests (No API Key)

```bash
# Run standard tests (direct backend testing)
pytest test_dao.py test_main.py
```

### Gateway Tests (With API Key)

```bash
# Test the mock gateway
pytest test_mock_gateway.py

# Test with integration marker (backend must be running)
pytest test_mock_gateway.py -m integration
```

### End-to-End Test

```bash
# 1. Start services
./start_local.sh

# 2. In another terminal, run tests
API_KEY="test-api-key-12345"
GATEWAY_URL="http://localhost:8001"

# Check stock
curl -H "x-api-key: $API_KEY" \
  "$GATEWAY_URL/api/inventory/store1/12345?quantity=10"

# Should return availability info
```

## Cost Considerations

### API Gateway Pricing

- **REST API**: $3.50 per million requests
- **Data Transfer**: $0.09/GB out
- **VPC Link**: $0.025/hour + $0.01/GB processed

### Optimization Tips

1. **Use Caching** - Enable response caching to reduce backend calls
2. **Compress Responses** - Enable gzip compression
3. **Monitor Usage** - Set up CloudWatch alarms for unexpected usage
4. **Right-size Limits** - Adjust rate limits based on actual needs

## Production Checklist

Before going to production:

- [ ] Change API key to secure value
- [ ] Enable CloudWatch logging
- [ ] Set appropriate rate limits
- [ ] Configure VPC Link for private access
- [ ] Enable X-Ray tracing
- [ ] Set up CloudWatch alarms
- [ ] Test all endpoints with production data
- [ ] Document API key distribution process
- [ ] Set up API key rotation policy
- [ ] Configure CORS if needed for web clients
- [ ] Enable AWS WAF for DDoS protection

## Files Reference

- `infrastructure/api_gateway.tf` - API Gateway Terraform configuration
- `infrastructure/security.tf` - Security group rules
- `inventory_api/mock_api_gateway.py` - Local mock gateway
- `inventory_api/start_local.sh` - Local development startup script
- `inventory_api/test_mock_gateway.py` - Gateway authentication tests

## Support

- **API Documentation**: http://localhost:8000/docs (backend)
- **Gateway Info**: http://localhost:8001/ (mock gateway)
- **Terraform Docs**: [API Gateway Resources](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/api_gateway_rest_api)

---

**Version:** 1.0.0  
**Last Updated:** February 13, 2026
