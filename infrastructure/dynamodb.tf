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