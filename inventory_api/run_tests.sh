#!/bin/bash
# Convenience script for running inventory API tests

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Inventory API Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "test_dao.py" ] || [ ! -f "test_main.py" ]; then
    echo -e "${RED}Error: Test files not found. Make sure you're in the inventory_api directory.${NC}"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${BLUE}Using virtual environment at .venv${NC}"
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo -e "${BLUE}Using virtual environment at venv${NC}"
    source venv/bin/activate
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}pytest is not installed. Installing test dependencies...${NC}"
    pip install -r requirements.txt
fi

# Parse command line arguments
COVERAGE=false
VERBOSE=false
SPECIFIC_TEST=""
MARKER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--marker)
            MARKER="$2"
            shift 2
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -c, --coverage     Run with coverage report"
            echo "  -v, --verbose      Run with verbose output"
            echo "  -m, --marker NAME  Run only tests with specific marker"
            echo "  -t, --test PATH    Run specific test file or function"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Run all tests"
            echo "  $0 -v                        # Run with verbose output"
            echo "  $0 -c                        # Run with coverage"
            echo "  $0 -t test_dao.py            # Run only DAO tests"
            echo "  $0 -m dynamodb               # Run only DynamoDB tests"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    echo -e "${BLUE}Running tests with coverage...${NC}"
    PYTEST_CMD="$PYTEST_CMD --cov=. --cov-report=html --cov-report=term"
fi

if [ -n "$MARKER" ]; then
    echo -e "${BLUE}Running tests with marker: $MARKER${NC}"
    PYTEST_CMD="$PYTEST_CMD -m $MARKER"
fi

if [ -n "$SPECIFIC_TEST" ]; then
    echo -e "${BLUE}Running specific test: $SPECIFIC_TEST${NC}"
    PYTEST_CMD="$PYTEST_CMD $SPECIFIC_TEST"
fi

echo -e "${BLUE}Command: $PYTEST_CMD${NC}"
echo ""

# Run the tests
if $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}   ✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage report generated at: htmlcov/index.html${NC}"
        echo -e "${BLUE}Open with: open htmlcov/index.html${NC}"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}   ✗ Tests failed${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
