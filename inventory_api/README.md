## Inventory API (FastAPI)

This service exposes inventory data (per–store stock and sale price) backed by the DynamoDB `products_by_store` table.

It is designed to be fronted by API Gateway for external vendors, but can also be run directly on an EC2 instance or locally for development.

### Table naming and configuration

The service follows the same convention as the Flask app:

- `DYNAMODB_PRODUCTS_TABLE` – full products table name, e.g. `product-catalogue-test-products`
- From that, the service derives:
  - `products_by_store` table name as `<prefix>-products_by_store`

Environment variables:

- **Required (one of):**
  - `DYNAMODB_PRODUCTS_TABLE` – e.g. `product-catalogue-test-products`, or
  - `NAME_PREFIX` – e.g. `product-catalogue-test` (then `DYNAMODB_PRODUCTS_TABLE` is inferred as `<NAME_PREFIX>-products`)
- **Optional:**
  - `AWS_REGION` or `AWS_DEFAULT_REGION` – if not set, boto3 will fall back to its default resolution

### Local development

From the repo root:

```bash
cd inventory_api

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

pip install -r requirements.txt
```

Export your AWS and table env vars (for the same account/region where Terraform created the tables):

```bash
export AWS_REGION=us-east-1
export NAME_PREFIX=product-catalogue-test
# or explicitly:
# export DYNAMODB_PRODUCTS_TABLE=product-catalogue-test-products
```

Run the API:

```bash
uvicorn main:app --reload --port 9000
```

Then test:

- Health: `GET http://localhost:9000/health`
- Inventory for a store: `GET http://localhost:9000/inventory/1234567890`
- One item: `GET http://localhost:9000/inventory/1234567890/4011`

### Notes for API Gateway / EC2

- **Deployment target:** You can run this on:
  - a small EC2 instance (systemd unit running `uvicorn`), or
  - as a container on ECS/Fargate, or
  - as a Lambda function via `fastapi` + ASGI adapter.
- **API Gateway:** Once the service is reachable (EC2 or ECS), you can:
  - Create a **HTTP API** or **REST API** in API Gateway
  - Point it at the service (ALB, NLB, or direct EC2 via VPC Link)
  - Add auth/rate-limiting per vendor (API keys, Cognito, etc.)

