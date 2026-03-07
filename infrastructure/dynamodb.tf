# DynamoDB Tables
#
# Data model aligns with server/seed_data:
#   products.json         -> products (barcode PK; GSIs by category)
#   stores.json           -> stores   (store_id PK)
#   products_by_store.json -> stock   (barcode PK, store_id SK) and sales (store_id PK, barcode SK); each row has store_id, barcode, quantity, percent_off, price


## Products table which includes Product details
resource "aws_dynamodb_table" "products" {
  name         = "${local.name_prefix}-products"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "barcode"

  attribute {
    name = "barcode"
    type = "S"
  }

  attribute {
    name = "primary_category"
    type = "S"
  }

  attribute {
    name = "category_path"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI_Category"
    hash_key        = "primary_category"
    range_key       = "category_path"
    projection_type = "ALL"
  }
}

# Stores table - one item per store (store_id, store_name, store_address)
resource "aws_dynamodb_table" "stores" {
  name         = "${local.name_prefix}-stores"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "store_id"

  attribute {
    name = "store_id"
    type = "S"
  }
}

# Stock Table - inventory per store (store_id PK, barcode SK)
resource "aws_dynamodb_table" "products_by_store" {
  name         = "${local.name_prefix}-products_by_store"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "store_id"
  range_key    = "barcode"

  attribute {
    name = "barcode"
    type = "S"
  }

  attribute {
    name = "store_id"
    type = "S"
  }
}

# Sales Events Table - records each inventory deduction (i.e. a sale) for reporting
# PK: store_id + SK: sale_id (ISO UTC timestamp + "#" + UUID) → time-range queries per store
# GSI on barcode → time-range queries per product (used for category-level reports)
resource "aws_dynamodb_table" "sales_events" {
  name         = "${local.name_prefix}-sales_events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "store_id"
  range_key    = "sale_id"

  attribute {
    name = "store_id"
    type = "S"
  }

  # Format: "YYYY-MM-DDTHH:mm:ss.ffffffZ#<uuid4>" — sortable by time, unique per event
  attribute {
    name = "sale_id"
    type = "S"
  }

  attribute {
    name = "barcode"
    type = "S"
  }

  # Allows querying all sales for a specific product across stores (for category reports)
  global_secondary_index {
    name            = "GSI_Barcode"
    hash_key        = "barcode"
    range_key       = "sale_id"
    projection_type = "ALL"
  }

  # Streams enable future Lambda triggers (e.g. real-time report generation)
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sales-events"
  })
}

# Report Schedules Table - stores recurring report configurations created by employees
# PK: schedule_id (UUID) — single-item lookups when Lambda runs or employee deletes
resource "aws_dynamodb_table" "report_schedules" {
  name         = "${local.name_prefix}-report_schedules"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "schedule_id"

  attribute {
    name = "schedule_id"
    type = "S"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-report-schedules"
  })
}

# Report Results Table - one record per generated report CSV
# PK: schedule_id + SK: generated_at — efficient listing of results per schedule (newest first)
resource "aws_dynamodb_table" "report_results" {
  name         = "${local.name_prefix}-report_results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "schedule_id"
  range_key    = "generated_at"

  attribute {
    name = "schedule_id"
    type = "S"
  }

  attribute {
    name = "generated_at"
    type = "S"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-report-results"
  })
}

resource "aws_dynamodb_table" "categories" {
  # NOTE: App code and seed script use a fixed, unprefixed categories table name.
  # See `server/data.py` (DYNAMODB_CATEGORIES_TABLE = 'categories') and `scripts/seed_dynamodb.sh`.
  name         = "categories"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "primary_category"
  range_key = "path"

  attribute {
    name = "primary_category"
    type = "S"
  }

  attribute {
    name = "path"
    type = "S"
  }

  attribute {
    name = "level"
    type = "N"
  }

  global_secondary_index {
    name            = "GSI_Level"
    hash_key        = "level"
    range_key       = "path"
    projection_type = "ALL"
  }
}