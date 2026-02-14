#!/bin/bash
# Test API Gateway endpoints for Inventory Service
# Fetches API Gateway URL and API key from Terraform outputs
# Tests all four public endpoints with various scenarios

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRASTRUCTURE_DIR="${INFRASTRUCTURE_DIR:-$PROJECT_ROOT/infrastructure}"

echo "=========================================="
echo "API GATEWAY ENDPOINT TESTS"
echo "=========================================="
echo ""

# Retrieve API Gateway details from Terraform outputs
echo "→ Fetching API Gateway configuration from Terraform..."
API_URL=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw api_gateway_url 2>/dev/null)
API_KEY=$(terraform -chdir="$INFRASTRUCTURE_DIR" output -raw api_key_value 2>/dev/null)

if [ -z "$API_URL" ] || [ -z "$API_KEY" ]; then
    echo "Error: Could not retrieve API Gateway URL or API key from Terraform outputs"
    echo "Make sure you have run 'terraform apply' first"
    exit 1
fi

echo "✓ API Gateway URL: $API_URL"
echo "✓ API Key retrieved"
echo ""

# Test configuration (using actual values from seed_data/products_by_store.json)
STORE_ID="1234567890"
BARCODE_1="0123456789012"  # Quantity: 24 in seed data
BARCODE_2="4011"            # Quantity: 45 in seed data

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter for tests
TOTAL_TESTS=0
PASSED_TESTS=0

# Helper function to run a test
run_test() {
    local test_name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    local expected_status="$5"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST $TOTAL_TESTS: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Method: $method"
    echo "Endpoint: $endpoint"
    if [ -n "$data" ]; then
        echo "Data: $data"
    fi
    echo ""
    
    # Make the request
    if [ -n "$data" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "x-api-key: $API_KEY" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "x-api-key: $API_KEY" \
            "$API_URL$endpoint")
    fi
    
    # Extract status code (last line) and body (everything before)
    HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    echo "Status Code: $HTTP_CODE"
    echo "Response Body:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    
    # Check if test passed
    if [ "$HTTP_CODE" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} - Got expected status code $expected_status"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAILED${NC} - Expected $expected_status but got $HTTP_CODE"
    fi
    echo ""
}

echo "=========================================="
echo "ENDPOINT 1: CHECK STOCK"
echo "GET /api/inventory/{store_id}/{barcode}"
echo "=========================================="
echo ""

# Test 1.1: Check stock - sufficient quantity
run_test "Check if store has sufficient stock (5 units)" \
    "GET" \
    "/api/inventory/$STORE_ID/$BARCODE_1?quantity=5" \
    "" \
    "200"

# Test 1.2: Check stock - different quantity
run_test "Check if store has sufficient stock (10 units)" \
    "GET" \
    "/api/inventory/$STORE_ID/$BARCODE_1?quantity=10" \
    "" \
    "200"

echo "=========================================="
echo "ENDPOINT 2: GET PRICE"
echo "GET /api/inventory/{store_id}/{barcode}/price"
echo "=========================================="
echo ""

# Test 2.1: Get price for product 1
run_test "Get price for product (including sales)" \
    "GET" \
    "/api/inventory/$STORE_ID/$BARCODE_1/price" \
    "" \
    "200"

# Test 2.2: Get price for product 2
run_test "Get price for different product" \
    "GET" \
    "/api/inventory/$STORE_ID/$BARCODE_2/price" \
    "" \
    "200"

echo "=========================================="
echo "ENDPOINT 3: DEDUCT SINGLE QUANTITY"
echo "PATCH /api/inventory/{store_id}/{barcode}"
echo "=========================================="
echo ""

# Test 3.1: Deduct small quantity
run_test "Deduct 2 units from inventory" \
    "PATCH" \
    "/api/inventory/$STORE_ID/$BARCODE_1" \
    '{"quantity": 2}' \
    "200"

# Test 3.2: Deduct another small quantity
run_test "Deduct 3 units from inventory" \
    "PATCH" \
    "/api/inventory/$STORE_ID/$BARCODE_1" \
    '{"quantity": 3}' \
    "200"

# Test 3.3: Try to deduct more than available (should fail)
run_test "Try to deduct excessive quantity (should fail)" \
    "PATCH" \
    "/api/inventory/$STORE_ID/$BARCODE_1" \
    '{"quantity": 99999}' \
    "400"

echo "=========================================="
echo "ENDPOINT 4: DEDUCT BATCH QUANTITIES"
echo "PATCH /api/inventory/{store_id}"
echo "=========================================="
echo ""

# Test 4.1: Batch deduct - small quantities
run_test "Batch deduct multiple products (small quantities)" \
    "PATCH" \
    "/api/inventory/$STORE_ID" \
    "{\"items\": [{\"barcode\": \"$BARCODE_1\", \"quantity\": 1}, {\"barcode\": \"$BARCODE_2\", \"quantity\": 2}]}" \
    "200"

# Test 4.2: Batch deduct - different products
run_test "Batch deduct different set of products" \
    "PATCH" \
    "/api/inventory/$STORE_ID" \
    "{\"items\": [{\"barcode\": \"$BARCODE_2\", \"quantity\": 1}]}" \
    "200"

echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $((TOTAL_TESTS - PASSED_TESTS))${NC}"
echo ""

if [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
