# DynamoDB Tables
#
# Data model aligns with server/seed_data:
#   products.json -> products (barcode PK; GSIs by category)
#   stores.json   -> stores   (store_id PK)
#   stock.json    -> stock   (barcode PK, store_id SK)
#   sales.json    -> sales   (store_id PK, barcode SK)

## Products table which includes Product details
resource "aws_dynamodb_table" "products" {
  name           = "${local.name_prefix}-products"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "barcode"
  # TODO: range_key of name?

  attribute {
    name = "barcode"
    type = "S"
  }

  #TODO: change this to nested? 
  attribute {
    name = "primary_category"
    type = "S"
  }

   attribute {
    name = "secondary_category"
    type = "S"
  }

  attribute {
    name = "tertiary_category"
    type = "S"
  }

  # GSI1. Search products by primary category
  global_secondary_index {
    name            = "PrimaryCategory"
    hash_key        = "primary_category"
    range_key       = "barcode"
    read_capacity   = 2
    write_capacity  = 2
    projection_type = "ALL"
  }

  # GSI2: By secondary_category
  global_secondary_index {
    name            = "SecondaryCategory"
    hash_key        = "secondary_category"
    range_key       = "barcode"
    read_capacity   = 2
    write_capacity  = 2
    projection_type = "ALL"
  }

  # GSI3: By tertiary_category
  global_secondary_index {
    name            = "TertiaryCategory"
    hash_key        = "tertiary_category"
    range_key       = "barcode"
    read_capacity   = 2
    write_capacity  = 2
    projection_type = "ALL"
  }
}

# Stores table - one item per store (store_id, store_name, store_address)
resource "aws_dynamodb_table" "stores" {
  name           = "${local.name_prefix}-stores"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "store_id"

  attribute {
    name = "store_id"
    type = "S"
  }
}

# Stock Table - TODO: May need to up capacity here.
resource "aws_dynamodb_table" "stock" {
  name           = "${local.name_prefix}-stock"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "barcode"
  range_key      = "store_id"

  attribute {
    name = "barcode"
    type = "S"
  }

  attribute {
    name = "store_id"
    type = "S"
  }
  

  # GSI: list stock by store (e.g. "all inventory at store X")
  global_secondary_index {
    name            = "ByStore"
    hash_key        = "store_id"
    range_key       = "barcode"
    read_capacity   = 2
    write_capacity  = 2
    projection_type = "ALL"
  }
}

# Sales table - per-store discounts (store_id, barcode, percent_off)
resource "aws_dynamodb_table" "sales" {
  name           = "${local.name_prefix}-sales"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "store_id"
  range_key      = "barcode"

  attribute {
    name = "store_id"
    type = "S"
  }

  attribute {
    name = "barcode"
    type = "S"
  }

  # GSI: list sales by product (e.g. "which stores have this on sale")
  global_secondary_index {
    name            = "ByProduct"
    hash_key        = "barcode"
    range_key       = "store_id"
    read_capacity   = 2
    write_capacity  = 2
    projection_type = "ALL"
  }
}