# DynamoDB Tables

# Stores Table
# Store Name
# Store ID
# Store Address

# Stock Table
# hash_key: productID
# range_key: storeID

# OR storeID + productID ==  main key
# storeId = secondary keyto allow for scan on secondary 
# index by store ID to get the initial call for ALL Products.  
# BUT THEN can also do CRUD On one product in one store.

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

# Stores Table - Store name & addresses
resource "aws_dynamodb_table" "stores" {
  name           = "${local.name_prefix}-stores"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "store_id"
  range_key      = "store_name"

  attribute {
    name = "store_id"
    type = "S"
  }

  attribute {
    name = "store_name"
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
  

  # TODO: ?? global_secondary_index Query stock across all stores?
}

# Comments Table
resource "aws_dynamodb_table" "comments" {
  name           = "${local.name_prefix}-comments"
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "taskId"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "S"
  }

  # GSI1: TaskCommentsIndex - Query comments by task, sorted by creation time
  global_secondary_index {
    name            = "TaskCommentsIndex"
    hash_key        = "taskId"
    range_key       = "createdAt"
    read_capacity   = 2
    write_capacity  = 2
    projection_type = "ALL"
  }
}