#!/bin/bash
# Traffic Generator — simulates POS sales against the inventory API.
#
# Fetches stores and inventory from the API, then repeatedly submits
# random POS sale baskets at the specified rate.
#
# Prerequisites: curl, jq, uuidgen (all available on macOS/standard Linux)
#
# Usage:
#   ./scripts/traffic_generator.sh [OPTIONS]
#
# Options:
#   --calls N   Number of POS sale calls to make (default: 20)
#   --rate  R   Calls per second, can be fractional (default: 2)
#   --url   URL Inventory API base URL (default: from terraform output)
#
# Examples:
#   ./scripts/traffic_generator.sh
#   ./scripts/traffic_generator.sh --calls 50 --rate 5
#   ./scripts/traffic_generator.sh --url http://1.2.3.4:9000 --calls 10 --rate 1

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
CALLS=20
RATE=2
INVENTORY_API_URL=""

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --calls) CALLS="$2";              shift 2 ;;
    --rate)  RATE="$2";               shift 2 ;;
    --url)   INVENTORY_API_URL="$2";  shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

# ── Resolve API URL ───────────────────────────────────────────────────────────
if [ -z "$INVENTORY_API_URL" ]; then
  echo "Getting inventory API URL from Terraform..."
  DNS=$(terraform -chdir="$PROJECT_ROOT/infrastructure" output -raw inventory_api_public_dns 2>/dev/null)
  if [ -z "$DNS" ]; then
    echo "ERROR: Could not get inventory_api_public_dns from terraform output."
    echo "       Pass --url http://<host>:9000 to specify the URL manually."
    exit 1
  fi
  INVENTORY_API_URL="http://${DNS}:9000"
fi

# Delay between calls in seconds (supports decimals via awk)
DELAY=$(awk "BEGIN {printf \"%.4f\", 1/$RATE}")

echo "=========================================="
echo "TRAFFIC GENERATOR"
echo "=========================================="
echo "  API:   $INVENTORY_API_URL"
echo "  Calls: $CALLS  Rate: ${RATE}/s  Delay: ${DELAY}s"
echo "=========================================="
echo ""

# ── Fetch stores from product catalogue API ───────────────────────────────────
CATALOGUE_URL=$(terraform -chdir="$PROJECT_ROOT/infrastructure" output -raw customer_api_alb_url 2>/dev/null)
if [ -z "$CATALOGUE_URL" ]; then
  echo "ERROR: Could not get customer_api_alb_url from terraform output."
  exit 1
fi
STORES_JSON=$(curl -sf "$CATALOGUE_URL/stores")
STORE_COUNT=$(echo "$STORES_JSON" | jq 'length')
if [ "$STORE_COUNT" -eq 0 ]; then
  echo "ERROR: No stores returned from $CATALOGUE_URL/stores"
  exit 1
fi
echo "  Found $STORE_COUNT stores"
echo ""

# ── Main loop ─────────────────────────────────────────────────────────────────
SUCCESSES=0
FAILURES=0

for i in $(seq 1 "$CALLS"); do
  # Pick a random store
  STORE_IDX=$(( RANDOM % STORE_COUNT ))
  STORE_ID=$(echo "$STORES_JSON" | jq -r ".[$STORE_IDX].store_id")

  # Fetch that store's current in-stock inventory
  INVENTORY_JSON=$(curl -sf "$INVENTORY_API_URL/inventory/$STORE_ID" || echo "[]")
  IN_STOCK=$(echo "$INVENTORY_JSON" | jq '[.[] | select(.quantity > 0)]')
  ITEM_COUNT=$(echo "$IN_STOCK" | jq 'length')

  if [ "$ITEM_COUNT" -eq 0 ]; then
    echo "  [$i/$CALLS] SKIP store=$STORE_ID — no stock (run restock.sh)"
    [ "$i" -lt "$CALLS" ] && sleep "$DELAY"
    continue
  fi

  # Pick 1–3 random distinct items from this store
  N_ITEMS=$(( (RANDOM % 3) + 1 ))
  if [ "$N_ITEMS" -gt "$ITEM_COUNT" ]; then N_ITEMS=$ITEM_COUNT; fi

  # Build items array: pick N_ITEMS unique random indices
  ITEMS_JSON="[]"
  USED_INDICES=""
  for _ in $(seq 1 "$N_ITEMS"); do
    while true; do
      IDX=$(( RANDOM % ITEM_COUNT ))
      # Ensure no duplicate barcodes in the basket
      if ! echo "$USED_INDICES" | grep -qw "$IDX"; then
        USED_INDICES="$USED_INDICES $IDX"
        break
      fi
    done
    BARCODE=$(echo "$IN_STOCK" | jq -r ".[$IDX].barcode")
    MAX_QTY=$(echo "$IN_STOCK" | jq -r ".[$IDX].quantity")
    QTY=$(( (RANDOM % 3) + 1 ))
    [ "$QTY" -gt "$MAX_QTY" ] && QTY=$MAX_QTY
    ITEMS_JSON=$(echo "$ITEMS_JSON" | jq ". + [{\"barcode\":\"$BARCODE\",\"quantity\":$QTY}]")
  done

  # Generate a unique transaction ID
  TXN_ID="TG-$(uuidgen | tr -d '-' | head -c 12 | tr '[:lower:]' '[:upper:]')"

  PAYLOAD=$(jq -n \
    --arg txn "$TXN_ID" \
    --argjson items "$ITEMS_JSON" \
    '{transaction_id: $txn, items: $items}')

  # Submit the POS sale
  HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "$INVENTORY_API_URL/api/pos/sale/$STORE_ID" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

  HTTP_BODY=$(echo "$HTTP_RESPONSE" | sed '$d')
  HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n 1)

  if [ "$HTTP_CODE" -eq 201 ]; then
    REVENUE=$(echo "$HTTP_BODY" | jq -r '.total_revenue')
    BARCODES=$(echo "$ITEMS_JSON" | jq -r '[.[].barcode] | join(", ")')
    echo "  [$i/$CALLS] OK   store=$STORE_ID  items=[$BARCODES]  revenue=\$$REVENUE"
    SUCCESSES=$(( SUCCESSES + 1 ))
  else
    DETAIL=$(echo "$HTTP_BODY" | jq -r '.detail // .error // "unknown error"' 2>/dev/null || echo "$HTTP_BODY")
    echo "  [$i/$CALLS] ERR  store=$STORE_ID  status=$HTTP_CODE  detail=$DETAIL"
    FAILURES=$(( FAILURES + 1 ))
  fi

  [ "$i" -lt "$CALLS" ] && sleep "$DELAY"
done

echo ""
echo "=========================================="
echo "  Done: $SUCCESSES succeeded, $FAILURES failed"
echo "=========================================="
