## Inventory API (FastAPI)

This service manages per-store inventory and records point-of-sale transactions. It is backed by two DynamoDB tables:

- `products_by_store` — current inventory state (mutable)
- `sales_events` — append-only log of sale transactions (used for reporting)

It is designed to be fronted by API Gateway for external vendors, but can also be run directly on an EC2 instance or locally for development.

### Design Decisions

**Sales API is co-located with the Inventory API (not a separate service)**

The POS endpoint (`POST /api/pos/sale/{store_id}`) atomically deducts inventory and records the sale event in a single request using DynamoDB `transact_write_items`. Splitting these into separate services would require distributed transactions or an eventual-consistency saga pattern, which is inappropriate for data used in financial reporting.

**Sales events are an append-only log (event sourcing)**

Each sale records `unit_price` (the discounted price at time of sale). This ensures that historical revenue calculations remain accurate even if prices change later. The `sales_events` table is never mutated — only appended to.

**One event record per basket line item**

A POS basket with N distinct products generates N `SaleEvent` records, all sharing a `transaction_id` from the POS terminal. This allows efficient DynamoDB queries by product (via `GSI_Barcode`) during report generation.

### Environment variables

- **Required (one of):**
  - `DYNAMODB_PRODUCTS_TABLE` – e.g. `product-catalogue-test-products`, or
  - `NAME_PREFIX` – e.g. `product-catalogue-test` (tables are inferred as `<NAME_PREFIX>-products`, `<NAME_PREFIX>-products_by_store`, `<NAME_PREFIX>-sales_events`)
- **Optional:**
  - `SALES_EVENTS_TABLE` – overrides the inferred sales events table name
  - `AWS_REGION` or `AWS_DEFAULT_REGION` – if not set, boto3 will fall back to its default resolution

### Local development

From the repo root:

```bash
cd inventory_api

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

pip install -r requirements.txt
```

**Using the `.env` file (recommended for local development):**

A `.env` file is provided in this directory with local development settings. The service automatically loads it if `python-dotenv` is installed (included in `requirements.txt`).

If you're using `uvicorn` directly, the `.env` file will be loaded automatically. If you need to manually load it:

```bash
# Load environment variables from .env file
export $(cat .env | xargs)

# Or source it (if your shell supports it):
# source .env
```

The `.env` file contains:
- `USE_DYNAMODB=0` – Disables DynamoDB, uses local JSON files from `../seed_data/products_by_store.json` instead
- Optional variables for DynamoDB mode (commented out) if you need to test against real tables

**Manual environment variable setup (alternative):**

If you prefer not to use the `.env` file, export variables manually:

```bash
# For local JSON mode (no DynamoDB):
export USE_DYNAMODB=0

# For DynamoDB mode (requires AWS credentials):
export AWS_REGION=us-east-1
export USE_DYNAMODB=1
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

