#!/bin/bash
# Start the Inventory API and Mock API Gateway for local testing

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
BACKEND_PORT=8000
GATEWAY_PORT=8001
API_KEY="test-api-key-12345"

echo -e "${BLUE}========================================"
echo -e "  Inventory API Local Development"
echo -e "========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found!${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        source venv/bin/activate
    fi
fi

# Parse command line arguments
MODE="both"
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            MODE="backend"
            shift
            ;;
        --gateway-only)
            MODE="gateway"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --backend-only   Start only the backend FastAPI server"
            echo "  --gateway-only   Start only the mock API Gateway"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Default: Starts both backend and gateway in background"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to check if port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to start backend
start_backend() {
    if port_in_use $BACKEND_PORT; then
        echo -e "${YELLOW}⚠️  Port $BACKEND_PORT is already in use${NC}"
        echo -e "${BLUE}Assuming backend is already running...${NC}"
    else
        echo -e "${BLUE}🚀 Starting Backend API on port $BACKEND_PORT...${NC}"
        uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT &
        BACKEND_PID=$!
        sleep 2
        if port_in_use $BACKEND_PORT; then
            echo -e "${GREEN}✓ Backend API running on http://localhost:$BACKEND_PORT${NC}"
        else
            echo -e "${RED}✗ Failed to start backend${NC}"
            exit 1
        fi
    fi
}

# Function to start gateway
start_gateway() {
    if port_in_use $GATEWAY_PORT; then
        echo -e "${YELLOW}⚠️  Port $GATEWAY_PORT is already in use${NC}"
        echo -e "${BLUE}Assuming gateway is already running...${NC}"
    else
        echo -e "${BLUE}🔑 Starting Mock API Gateway on port $GATEWAY_PORT...${NC}"
        export BACKEND_URL="http://localhost:$BACKEND_PORT"
        export MOCK_API_KEY="$API_KEY"
        export MOCK_PORT="$GATEWAY_PORT"
        python mock_api_gateway.py &
        GATEWAY_PID=$!
        sleep 2
        if port_in_use $GATEWAY_PORT; then
            echo -e "${GREEN}✓ Mock API Gateway running on http://localhost:$GATEWAY_PORT${NC}"
        else
            echo -e "${RED}✗ Failed to start gateway${NC}"
            exit 1
        fi
    fi
}

# Start services based on mode
if [ "$MODE" = "backend" ]; then
    start_backend
    wait
elif [ "$MODE" = "gateway" ]; then
    start_gateway
    wait
else
    start_backend
    start_gateway
    
    echo ""
    echo -e "${GREEN}========================================"
    echo -e "  ✓ Services Started Successfully!"
    echo -e "========================================${NC}"
    echo ""
    echo -e "${BLUE}📍 Backend API:${NC}"
    echo -e "   http://localhost:$BACKEND_PORT"
    echo -e "   Docs: http://localhost:$BACKEND_PORT/docs"
    echo ""
    echo -e "${BLUE}🔑 Mock API Gateway (with API key):${NC}"
    echo -e "   http://localhost:$GATEWAY_PORT"
    echo -e "   API Key: ${GREEN}$API_KEY${NC}"
    echo ""
    echo -e "${YELLOW}💡 Example requests:${NC}"
    echo ""
    echo -e "${BLUE}# Check stock${NC}"
    echo -e "curl -H 'x-api-key: $API_KEY' \\"
    echo -e "  'http://localhost:$GATEWAY_PORT/api/inventory/store1/12345?quantity=10'"
    echo ""
    echo -e "${BLUE}# Get price${NC}"
    echo -e "curl -H 'x-api-key: $API_KEY' \\"
    echo -e "  'http://localhost:$GATEWAY_PORT/api/inventory/store1/12345/price'"
    echo ""
    echo -e "${BLUE}# Deduct single${NC}"
    echo -e "curl -X PATCH -H 'x-api-key: $API_KEY' \\"
    echo -e "  -H 'Content-Type: application/json' \\"
    echo -e "  -d '{\"quantity\": 5}' \\"
    echo -e "  'http://localhost:$GATEWAY_PORT/api/inventory/store1/12345'"
    echo ""
    echo -e "${BLUE}# Deduct batch${NC}"
    echo -e "curl -X PATCH -H 'x-api-key: $API_KEY' \\"
    echo -e "  -H 'Content-Type: application/json' \\"
    echo -e "  -d '{\"items\": [{\"barcode\": \"12345\", \"quantity\": 2}]}' \\"
    echo -e "  'http://localhost:$GATEWAY_PORT/api/inventory/store1'"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop both services${NC}"
    echo ""
    
    # Wait for both processes
    wait
fi
