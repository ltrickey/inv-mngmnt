#!/usr/bin/env bash
# Seed DynamoDB tables from server/seed_data JSON files.
# Can run locally (with Terraform) or on EC2 (with NAME_PREFIX or DYNAMODB_PRODUCTS_TABLE set).
# Requires: jq, aws CLI. Set SEED_DATA_DIR if not running from repo/deploy root.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# Seed data is now at the repo root: ./seed_data
SEED_DATA_DIR="${SEED_DATA_DIR:-$PROJECT_ROOT/seed_data}"
INFRASTRUCTURE_DIR="${INFRASTRUCTURE_DIR:-$PROJECT_ROOT/infrastructure}"

# Convert JSON object to DynamoDB Item format (omit null). Use with: jq -c 'def dynamo_val: ...; def to_item: ...; .[] | to_item'
JQ_TO_ITEM='
def dynamo_val:
  if type == "string" then {S: .}
  elif type == "number" then {N: (.|tostring)}
  elif type == "boolean" then {BOOL: .}
  elif type == "array" then {L: [.[] | dynamo_val]}
  elif type == "object" then {M: (to_entries | map({key: .key, value: (.value | dynamo_val)}) | from_entries)}
  else empty end;
def to_item: to_entries | map(select(.value != null)) | map({key: .key, value: (.value | dynamo_val)}) | from_entries;
.[] | to_item
'

# For products: add top-level primary_category from category.primary so GSI_Category works
JQ_TO_ITEM_PRODUCTS='
def dynamo_val:
  if type == "string" then {S: .}
  elif type == "number" then {N: (.|tostring)}
  elif type == "boolean" then {BOOL: .}
  elif type == "array" then {L: [.[] | dynamo_val]}
  elif type == "object" then {M: (to_entries | map({key: .key, value: (.value | dynamo_val)}) | from_entries)}
  else empty end;
def to_item: to_entries | map(select(.value != null)) | map({key: .key, value: (.value | dynamo_val)}) | from_entries;
.[] | (. + {primary_category: .category.primary}) | to_item
'

seed_table() {
  local table_suffix="$1"
  local file="$2"
  local label="$3"
  local jq_program="${4:-$JQ_TO_ITEM}"
  local table_name
  if [ "$table_suffix" = "categories" ]; then
    table_name="categories"
  else
    table_name="${NAME_PREFIX}-${table_suffix}"
  fi

  if [ ! -f "$file" ]; then
    echo "  Skipping $label: file not found $file"
    return 0
  fi

  local count=0
  local batch=()
  local batch_size=25

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    batch+=("$line")
    if [ "${#batch[@]}" -eq "$batch_size" ]; then
      local first="${batch[0]}"
      local rest=("${batch[@]:1}")
      local items_json="[$first$(printf ',%s' "${rest[@]}")]"
      local requests
      requests=$(echo "$items_json" | jq -c '[.[] | {PutRequest: {Item: .}}]')
      local payload
      payload=$(jq -n --arg t "$table_name" --argjson r "$requests" '{} | .[$t] = $r')
      aws dynamodb batch-write-item --request-items "$payload" --no-cli-pager >/dev/null
      count=$((count + ${#batch[@]}))
      batch=()
    fi
  done < <(jq -c "$jq_program" "$file")

  if [ "${#batch[@]}" -gt 0 ]; then
    local first="${batch[0]}"
    local rest=("${batch[@]:1}")
    local items_json="[$first$(printf ',%s' "${rest[@]}")]"
    local requests
    requests=$(echo "$items_json" | jq -c '[.[] | {PutRequest: {Item: .}}]')
    local payload
    payload=$(jq -n --arg t "$table_name" --argjson r "$requests" '{} | .[$t] = $r')
    aws dynamodb batch-write-item --request-items "$payload" --no-cli-pager >/dev/null
    count=$((count + ${#batch[@]}))
  fi

  if [ "$count" -gt 0 ]; then
    echo "  $label: $count items -> $table_name"
  fi
}

# --- main ---
if [ ! -d "$SEED_DATA_DIR" ]; then
  echo "Error: Seed data directory not found: $SEED_DATA_DIR" >&2
  exit 1
fi

# Resolve NAME_PREFIX: from env, or from DYNAMODB_PRODUCTS_TABLE (e.g. on EC2), or from Terraform (local)
if [ -z "$NAME_PREFIX" ] && [ -n "$DYNAMODB_PRODUCTS_TABLE" ]; then
  NAME_PREFIX="${DYNAMODB_PRODUCTS_TABLE%-products}"
fi
if [ -z "$NAME_PREFIX" ] && [ -f "$INFRASTRUCTURE_DIR/dynamodb.tf" ]; then
  NAME_PREFIX=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw name_prefix 2>/dev/null) || true
fi
if [ -z "$NAME_PREFIX" ]; then
  echo "Error: Set NAME_PREFIX or DYNAMODB_PRODUCTS_TABLE, or run from repo with Terraform applied." >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required. Install jq to run this script." >&2
  exit 1
fi
if ! command -v aws &>/dev/null; then
  echo "Error: AWS CLI is required. Install aws-cli and configure credentials." >&2
  exit 1
fi

# Optional: use same region as Terraform
if [ -z "$AWS_REGION" ] && [ -z "$AWS_DEFAULT_REGION" ]; then
  AWS_REGION=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw aws_region 2>/dev/null) || true
  [ -n "$AWS_REGION" ] && export AWS_DEFAULT_REGION="$AWS_REGION"
fi

echo "Seeding DynamoDB (prefix=$NAME_PREFIX) from $SEED_DATA_DIR"
seed_table "products"           "$SEED_DATA_DIR/products.json"           "Products"           "$JQ_TO_ITEM_PRODUCTS"
seed_table "stores"             "$SEED_DATA_DIR/stores.json"             "Stores"
seed_table "products_by_store"  "$SEED_DATA_DIR/products_by_store.json"  "Products by store"
seed_table "categories"         "$SEED_DATA_DIR/categories.json"         "Categories"
echo "DynamoDB seeding complete."
