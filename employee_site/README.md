# Employee Inventory Management Site

Internal employee-only website for managing store inventory. Gated behind AWS Cognito authentication.

## Architecture

```
React SPA (S3)  →  Flask BFF (Docker)  →  Inventory API (FastAPI / EC2)
                                       →  Product Catalogue (Flask / EC2)
```

## Directory Layout

```
employee_site/
  site/           React frontend (Vite)
  server/         Flask backend-for-frontend (BFF)
  scripts/        CLI utilities (e.g. create Cognito users)
```

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- The existing `server` (product catalogue) running on port 8000
- The existing `inventory_api` running on port 9000

### 1. Start the Product Catalogue and Inventory API

```bash
# Terminal 1 – Product Catalogue
cd server && flask run --port 8000

# Terminal 2 – Inventory API
cd inventory_api && uvicorn main:app --port 9000
```

### 2. Start the Employee BFF

```bash
cd employee_site/server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py          # runs on port 5001, SKIP_AUTH=1 by default in .env
```

### 3. Start the React Dev Server

```bash
cd employee_site/site
npm install
npm run dev            # runs on port 3001, proxies /api/* to port 5001
```

Open http://localhost:3001. With `SKIP_AUTH=1`, the login screen still appears
but you can enter any credentials (they are not validated).

### Production Environment Variables

#### React SPA (build-time)

| Variable | Description |
|---|---|
| `VITE_COGNITO_USER_POOL_ID` | Cognito User Pool ID |
| `VITE_COGNITO_APP_CLIENT_ID` | Cognito App Client ID |
| `VITE_API_BASE_URL` | Full URL to the Flask BFF (e.g. `https://bff.example.com`) |

#### Flask BFF (runtime)

| Variable | Description |
|---|---|
| `COGNITO_USER_POOL_ID` | Cognito User Pool ID |
| `COGNITO_APP_CLIENT_ID` | Cognito App Client ID |
| `AWS_REGION` | AWS region (default: `us-east-1`) |
| `PRODUCT_CATALOGUE_API_URL` | URL of the product catalogue Flask server |
| `INVENTORY_API_URL` | URL of the FastAPI inventory service |
| `SKIP_AUTH` | Set to `1` to skip JWT validation (dev only) |

## Docker

```bash
cd employee_site/server
docker build -t employee-bff .
docker run -p 5001:5001 \
  -e COGNITO_USER_POOL_ID=us-east-1_XXXXX \
  -e COGNITO_APP_CLIENT_ID=abc123 \
  -e AWS_REGION=us-east-1 \
  -e PRODUCT_CATALOGUE_API_URL=http://catalogue-host:8000 \
  -e INVENTORY_API_URL=http://inventory-host:9000 \
  employee-bff
```

## Deployment to AWS

### Prerequisites

- **Docker Desktop** — must be running locally. The deploy script builds the BFF Docker image and pushes it to ECR during `terraform apply`.
- **AWS CLI** — configured with valid credentials (`~/.aws/credentials`). For Learner Lab, re-copy credentials each session.
- **Node.js 18+** — used to build the React frontend before uploading to S3.
- **Terraform** — the infrastructure is defined in `infrastructure/`.

### How it works

Running `terraform apply` from the `infrastructure/` directory will:

1. Provision all AWS resources (ECR, ECS Fargate, ALB, S3, Cognito, etc.)
2. Automatically trigger `scripts/deploy_employee_site.sh`, which:
   - Builds the BFF Docker image and pushes it to ECR
   - Builds the React frontend with production env vars and uploads to S3
   - Forces the ECS service to pull the latest image

### Re-deploying after code changes

```bash
cd infrastructure
terraform apply
```

Terraform detects changes and re-runs the deploy script. If only the employee site code changed (no infrastructure changes), you can also run the deploy script directly:

```bash
ECR_REPOSITORY_URL=<ecr_url> \
COGNITO_USER_POOL_ID=<pool_id> \
COGNITO_APP_CLIENT_ID=<client_id> \
EMPLOYEE_BFF_ALB_URL=<alb_url> \
EMPLOYEE_SITE_BUCKET=<bucket> \
ECS_CLUSTER=<cluster_name> \
ECS_SERVICE=<service_name> \
./scripts/deploy_employee_site.sh
```

All values are available from `terraform output`.

## Creating Employee Users

After deploying the Cognito User Pool via Terraform:

```bash
cd employee_site/scripts
python create_user.py \
  --email alice@store.com \
  --username alice \
  --user-pool-id us-east-1_XXXXX \
  --region us-east-1
```

The user will receive a temporary password and must change it on first login.
