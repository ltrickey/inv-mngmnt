# System Design

Inventory & POS management system with two front doors: a public product-catalogue site for customers and a Cognito-gated internal tool for employees to manage stock and schedule sales reports. See [SystemDiagram.wsd](SystemDiagram.wsd) for the visual.

## Layers

- **React SPAs (2)** — static sites served from S3.
  - `customer_site/site` — public product browsing, category filters, store/stock lookup. No auth.
  - `employee_site/site` — Cognito login, stock table + add/edit product, report scheduling UI.
- **Flask (2 apps, different roles)**
  - `customer_site/server` — talks **directly to DynamoDB** for its own product-catalogue reads (`products`, `stores`, `categories`, `products_by_store`). Not a BFF: a BFF's defining trait is orchestrating/proxying calls to *other* backend services on behalf of a frontend, without owning much data itself. This service owns its data path outright, so it's just a normal single-purpose API backend for the customer SPA.
  - `employee_site/server` — the real **BFF**: its main job is orchestration, not data ownership. Cognito JWT-verified on every request, it proxies catalogue reads to the customer-site Flask app and inventory operations to FastAPI rather than talking to those tables itself. The one thing it does own directly is report scheduling (writes `report_schedules`/`report_results`, creates EventBridge Scheduler schedules, issues S3 presigned URLs for downloads) — everything else is orchestration on behalf of the employee SPA.
- **FastAPI** (`inventory_api`) — containerized, runs on ECS Fargate (`infrastructure/fastapi_site.tf`), talks directly to DynamoDB. No public ALB of its own — the single path in is the internal NLB defined in `api_gateway.tf`, used by both internal callers (employee BFF, over the VPC) and the external vendor-facing API Gateway route. (Originally ran on a bare EC2 instance — a constraint of the AWS Academy class this project started in — migrated to Fargate to match the other two services.)
- **DynamoDB** — see Data Model below.
- **Lambda + EventBridge** — `report_lambda` generates report CSVs. Not a single fixed schedule: the BFF creates a per-user **EventBridge Scheduler** schedule when a report is configured, which invokes the Lambda on its cadence.
- **Cognito** — one user pool, employee-only (admin-created users, no self-signup). Enforced in `employee_site/server/auth.py`.
- **Terraform** (`infrastructure/`) — provisions all of the above: ECS Fargate + ALB for both Flask apps, S3 static sites for both SPAs, ECS Fargate for FastAPI (registered into the internal NLB, no public ALB), API Gateway + VPC Link, DynamoDB tables, the report Lambda + EventBridge Scheduler group, Cognito user pool/client, S3 buckets for product images and report output. All three backend services share one ECR-per-service / Fargate-task-definition pattern and one IAM execution/task role.

## Component summary

| Component | Responsibility | Runs on |
|---|---|---|
| customer SPA | Public product browsing | S3 static site |
| employee SPA | Stock mgmt, report scheduling, login | S3 static site |
| customer Flask | Public catalogue API, direct-to-DynamoDB | ECS Fargate + ALB |
| employee Flask (BFF) | Auth gate, proxies catalogue + inventory, owns report schedules | ECS Fargate + ALB |
| FastAPI | Inventory/POS CRUD, vendor API | ECS Fargate (behind internal NLB, no public ALB) |
| report Lambda | Builds report CSVs on schedule | Lambda |
| Cognito | Employee auth | Managed |
| Terraform | Provisions everything above | N/A |

## Data Model

DynamoDB tables (actual, evolved past the original 3-4 table sketch):

- **products** — PK `barcode`. GSI on `category`. Product catalogue details (name, description, price, ingredients, image_url).
- **stores** — PK `store_id`. Store info for the store selector.
- **categories** — fixed lookup table for product category taxonomy.
- **products_by_store** — PK `store_id`, SK `barcode`. Serves both stock levels and per-store pricing (`quantity`, `price`, `percent_off`) — one table instead of separate stock/sales tables, since both are keyed the same way.
- **sales_events** — PK `store_id`, SK `sale_id`. GSI on `barcode`. DynamoDB Streams enabled. POS transaction log; source of truth for reporting. High write volume, append-only.
- **report_schedules** — user-configured recurring report definitions (cadence, filters), written by the employee BFF.
- **report_results** — completed report runs (S3 key, status, timestamps), written by the report Lambda.

Original design intent (kept for reference): stock needed high write throughput (~10 TPS) while sales needed high read / low write (~1 write/day), which is why they were considered separately. In practice, `products_by_store` covers stock+pricing, and `sales_events` — added later for POS transaction logging — ended up covering what "sales" was meant to be, since reports are built by aggregating discrete sale events rather than reading a rolled-up sales table.

## Request flows

- **Customer browsing**: customer SPA → customer Flask → DynamoDB (`products`, `stores`, `categories`, `products_by_store`) directly. FastAPI is not in this path.
- **Employee stock edit**: employee SPA → employee Flask (BFF, Cognito-verified) → FastAPI (`/inventory/{store_id}/{barcode}`) → DynamoDB.
- **POS sale (vendor)**: external vendor → API Gateway (API key) → VPC Link → internal NLB → FastAPI on ECS Fargate (`/api/pos/sale/{store_id}`) → atomic deduction against `products_by_store` + write to `sales_events`.
- **Scheduled report**: employee SPA → employee Flask BFF creates a `report_schedules` row and an EventBridge Scheduler schedule → EventBridge invokes `report_lambda` on cadence → Lambda reads `sales_events`, aggregates, writes CSV to S3, writes a `report_results` row → employee BFF issues a presigned S3 URL for download.
