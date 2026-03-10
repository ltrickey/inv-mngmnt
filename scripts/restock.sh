#!/bin/bash
# Restock Script — resets inventory quantities so the traffic generator
# can run again without running out of stock.
#
# Prerequisites: curl, jq (all available on macOS/standard Linux)
#
# Usage:
#   ./scripts/restock.sh [OPTIONS]
#
# Options:
#   --quantity N   Quantity to set for each item (default: 500)
#   --url      URL Inventory API base URL (default: from terraform output)
#   --low-only     Only restock items at or below --threshold
#   --threshold N  Low-stock threshold for --low-only mode (default: 10)
#
# Examples:
#   ./scripts/restock.sh
#   ./scripts/restock.sh --low-only --threshold 20
#   ./scripts/restock.sh --url http://1.2.3.4:9000 --quantity 1000

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
RESTOCK_QTY=500
INVENTORY_API_URL=""
LOW_ONLY=false
THRESHOLD=10

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --quantity)  RESTOCK_QTY="$2";      shift 2 ;;
    --url)       INVENTORY_API_URL="$2"; shift 2 ;;
    --low-only)  LOW_ONLY=true;          shift   ;;
    --threshold) THRESHOLD="$2";         shift 2 ;;
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

echo "=========================================="
echo "RESTOCK"
echo "=========================================="
echo "  API:      $INVENTORY_API_URL"
echo "  Quantity: $RESTOCK_QTY"
if [ "$LOW_ONLY" = true ]; then
  echo "  Mode:     low-stock only (current qty <= $THRESHOLD)"
else
  echo "  Mode:     all items"
fi
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
echo "Found $STORE_COUNT stores"
echo ""

# ── Restock each store ────────────────────────────────────────────────────────
TOTAL_UPDATED=0
TOTAL_SKIPPED=0
TOTAL_FAILED=0

for i in $(seq 0 $(( STORE_COUNT - 1 ))); do
  STORE_ID=$(echo "$STORES_JSON" | jq -r ".[$i].store_id")
  STORE_NAME=$(echo "$STORES_JSON" | jq -r ".[$i].store_name")

  INVENTORY_JSON=$(curl -sf "$INVENTORY_API_URL/inventory/$STORE_ID" || echo "[]")
  ITEM_COUNT=$(echo "$INVENTORY_JSON" | jq 'length')

  UPDATED=0
  SKIPPED=0
  FAILED=0

  for j in $(seq 0 $(( ITEM_COUNT - 1 ))); do
    BARCODE=$(echo "$INVENTORY_JSON" | jq -r ".[$j].barcode")
    CURRENT_QTY=$(echo "$INVENTORY_JSON" | jq -r ".[$j].quantity // 0")

    # Skip if --low-only and item is above threshold
    if [ "$LOW_ONLY" = true ] && [ "$CURRENT_QTY" -gt "$THRESHOLD" ]; then
      SKIPPED=$(( SKIPPED + 1 ))
      continue
    fi

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
      "$INVENTORY_API_URL/inventory/$STORE_ID/$BARCODE" \
      -H "Content-Type: application/json" \
      -d "{\"quantity\":$RESTOCK_QTY}")

    if [ "$HTTP_CODE" -eq 200 ]; then
      UPDATED=$(( UPDATED + 1 ))
    else
      FAILED=$(( FAILED + 1 ))
      echo "  WARNING: failed to restock $BARCODE at $STORE_ID (HTTP $HTTP_CODE)"
    fi
  done

  echo "  $STORE_NAME: updated=$UPDATED  skipped=$SKIPPED  failed=$FAILED"
  TOTAL_UPDATED=$(( TOTAL_UPDATED + UPDATED ))
  TOTAL_SKIPPED=$(( TOTAL_SKIPPED + SKIPPED ))
  TOTAL_FAILED=$(( TOTAL_FAILED + FAILED ))
done

echo ""
echo "=========================================="
echo "  Done: updated=$TOTAL_UPDATED  skipped=$TOTAL_SKIPPED  failed=$TOTAL_FAILED"
echo "=========================================="
