# Grocery Store Inventory Management

A multi-tenant grocery inventory & POS system: a public product-catalogue site for customers, a Cognito-gated internal tool for employees to manage stock and schedule sales reports, and a vendor-facing API for point-of-sale integrations. Two React SPAs, two Flask services in different roles (one direct-to-database, one a real backend-for-frontend), a FastAPI inventory/POS service, scheduled reporting via Lambda + EventBridge, and DynamoDB — all containerized on ECS Fargate and provisioned end-to-end with Terraform.

Originally built as a homework series for CPSC 5910 (Cloud Computing, Seattle University); since then FastAPI has been migrated off a class-required bare EC2 instance onto ECS Fargate to match the other two services.

Products/stores/categories data access lives in a top-level **`catalog/`** package rather than nested under `customer_site/`, since those tables are core domain data, not something specific to the customer-facing site. `customer_site/server` is its sole consumer today; `inventory_api` only imports `catalog/dynamo.py` for its table-naming convention, since it owns a different table (`products_by_store`) with its own DAO. `customer_site/server` no longer has a direct-DynamoDB fallback for stock/sales data — that would have duplicated `inventory_api`'s DAO for the same table, so it proxies to the inventory API (or falls back to local JSON, for offline dev) instead.

## Documentation

- **[SystemDesign.md](SystemDesign.md)** — architecture narrative: layers, component responsibilities, data model, and request flows
- **[SystemDiagram.wsd](SystemDiagram.wsd)** — PlantUML architecture diagram (render with the PlantUML CLI/plugin, or paste into [plantuml.com](https://www.plantuml.com/plantuml))
- **[data.puml](data.puml)** — entity-relationship sketch of the core DynamoDB tables
- **[infrastructure/README.md](infrastructure/README.md)** — Terraform reference: variables, security groups, IAM, deployment scripts

## Run Locally

The fastest way to get all three backend services running together is Docker Compose — no AWS credentials needed, since each service falls back to local JSON seed data / no-auth mode:

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Inventory API (FastAPI) | http://localhost:9000 (docs at `/docs`) |
| Customer API (Flask) | http://localhost:8000 |
| Employee BFF (Flask) | http://localhost:5001 |

To run a React frontend against it:

```bash
cd customer_site/site && npm install && npm run dev   # http://localhost:5173, talks to :8000
# or
cd employee_site/site && npm install && npm run dev   # talks to :5001, SKIP_AUTH=1 bypasses Cognito
```

### Running services individually (without Docker)

Each backend service can also run directly with a virtualenv. All three default to `USE_DYNAMODB=0` (or `SKIP_AUTH=1` for the employee BFF), which reads from `seed_data/` instead of requiring AWS credentials.

```bash
# Inventory API
cd inventory_api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 9000

# Customer API (separate terminal)
cd customer_site/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
INVENTORY_API_BASE_URL=http://127.0.0.1:9000 python app.py   # :8000

# Employee BFF (separate terminal)
cd employee_site/server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SKIP_AUTH=1 PRODUCT_CATALOGUE_API_URL=http://127.0.0.1:8000 INVENTORY_API_URL=http://127.0.0.1:9000 python app.py   # :5001
```

Seed data (`seed_data/products.json`, `stores.json`, `products_by_store.json`, `categories.json`) lives at the repo root and is shared by both the Customer API and the Inventory API in local mode.

## Deploying to AWS

Full infrastructure — three ECS Fargate services, S3 static sites, DynamoDB, API Gateway, Cognito, and the report Lambda — is provisioned and deployed with a single `terraform apply`. See **[infrastructure/README.md](infrastructure/README.md)** for the complete reference (variables, security groups, IAM, troubleshooting).

### Prerequisites

- **AWS credentials** — set as environment variables or in `~/.aws/credentials`. For AWS Academy/Learner Lab, credentials are temporary and expire — re-copy them each session.
- **Terraform** — [install](https://developer.hashicorp.com/terraform/downloads)
- **AWS CLI** — [install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Docker Desktop** — must be running; used to build and push all three service images to ECR
- **Node.js 18+** and **npm** — used to build the two React frontends before uploading to S3
- **jq** — used by `seed_dynamodb.sh`

### Setting AWS credentials

```bash
# Temporary credentials (AWS Academy/Learner Lab — Access Key starts with "ASIA")
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_SESSION_TOKEN="your-session-token"

# Permanent credentials — omit AWS_SESSION_TOKEN
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
```

Verify with `echo $AWS_ACCESS_KEY_ID`. "InvalidClientTokenId" errors usually mean expired temporary credentials — download a fresh set.

### Deploy

```bash
cd infrastructure
terraform init    # first time only
terraform apply   # builds all three Docker images, pushes to ECR, deploys, seeds DynamoDB
```

`terraform apply` will prompt for `yes` to confirm.

**What it does:**
1. Creates AWS infrastructure — ECS Fargate clusters + ALBs for the customer and employee sites, ECS Fargate + internal NLB for the inventory API, ECR repos, S3 buckets, DynamoDB tables, API Gateway, Cognito, the report Lambda + EventBridge Scheduler group
2. Uploads product images to S3
3. Builds and pushes the Inventory API Docker image, deploys to ECS Fargate
4. Seeds DynamoDB tables with product data
5. Builds and pushes the Customer API Docker image, builds the React frontend, uploads to S3, deploys to ECS Fargate
6. Builds and pushes the Employee BFF Docker image, builds the React frontend, uploads to S3, deploys to ECS Fargate

**Create an employee user** (required to log into the employee site — admin-created only, no self-signup):

```bash
./scripts/create_employee_user.sh --email <your-email>
```

**Access the applications:**
```bash
terraform output customer_site_url    # Customer SPA (S3 static site)
terraform output employee_site_url    # Employee SPA (S3 static site)
terraform output api_gateway_url      # Vendor-facing API Gateway
```

### Trying the reporting pipeline end-to-end

1. Log into the employee site with the temporary password from `create_employee_user.sh`
2. Go to the **Reports** tab → add a new schedule (e.g. every minute, filtered by store or category)
3. Generate some sales activity:
   ```bash
   ./scripts/traffic_generator.sh --calls 50 --rate 5
   ```
4. Restock afterward if needed:
   ```bash
   ./scripts/restock.sh --low-only --threshold 10
   ```
5. Watch the scheduled report land in the Reports tab as a downloadable CSV

### Tearing down

```bash
cd infrastructure
terraform destroy
```

If a Learner Lab session ends before you run `terraform destroy`, the state can go stale. To reset:
```bash
cp infrastructure/terraform.tfstate infrastructure/terraform.tfstate.old-lab
rm -f infrastructure/terraform.tfstate infrastructure/terraform.tfstate.backup
rm -rf infrastructure/.terraform
```
