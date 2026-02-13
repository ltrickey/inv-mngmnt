# Inventory API Testing Guide

This directory contains comprehensive tests for the Inventory API service, including both DAO (Data Access Object) layer tests and FastAPI endpoint tests.

## Testing Framework

We use **pytest** as the primary testing framework, along with:

- **pytest-asyncio** - For async test support
- **httpx** - For HTTP client testing (used by FastAPI TestClient)
- **moto** - For mocking AWS services (DynamoDB)
- **pytest-mock** - For advanced mocking capabilities

## Installation

Install test dependencies:

```bash
pip install -r requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Specific Test File

```bash
# DAO tests only
pytest test_dao.py

# API endpoint tests only
pytest test_main.py
```

### Run Specific Test Class or Function

```bash
# Run all tests in a specific class
pytest test_dao.py::TestInventoryDAOJson

# Run a specific test function
pytest test_dao.py::TestInventoryDAOJson::test_deduct_quantity_success
```

### Run Tests by Marker

Tests are organized with markers for easy filtering:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only DynamoDB-related tests
pytest -m dynamodb

# Run only JSON file-based tests
pytest -m json
```

### Run with Coverage Report

To see code coverage:

```bash
# Install pytest-cov first
pip install pytest-cov

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Open HTML report
open htmlcov/index.html
```

## Test Structure

### test_dao.py

Comprehensive tests for both DAO implementations:

- **TestInventoryDAOJson**: Tests for JSON file-based storage
  - CRUD operations (Create, Read, Update, Delete)
  - Quantity deduction (single and batch)
  - Atomic operations validation
  - Error handling (insufficient stock, item not found)
  
- **TestInventoryDAODynamoDB**: Tests for DynamoDB storage
  - All JSON tests, but with DynamoDB backend
  - Uses `moto` to mock DynamoDB service
  - Tests transaction atomicity
  
- **TestInventoryItemModel**: Tests for the Pydantic data model

### test_main.py

Integration tests for FastAPI endpoints:

- **TestHealthEndpoint**: Health check endpoint tests
- **TestListInventoryEndpoint**: GET /inventory/{store_id}
- **TestGetInventoryItemEndpoint**: GET /inventory/{store_id}/{barcode}
- **TestAPIHeaders**: Content-Type and CORS validation
- **TestOpenAPIDocumentation**: OpenAPI schema validation
- **TestErrorHandling**: Error scenarios and edge cases
- **TestDAOIntegration**: Integration between endpoints and DAO layer

## Test Coverage Areas

### DAO Layer Tests

✅ **Get Operations**
- Retrieve all items by store ID
- Retrieve specific item by store ID and barcode
- Handle missing items gracefully

✅ **Deduct Quantity Operations**
- Single item quantity deduction
- Batch quantity deduction (multiple items)
- Validate sufficient stock before deduction
- Atomic transaction behavior (all-or-nothing)

✅ **Error Handling**
- Insufficient quantity errors
- Item not found errors
- Invalid data handling
- File I/O errors (JSON)
- DynamoDB errors

✅ **Edge Cases**
- Empty inventory
- Zero quantity
- Exact quantity deduction
- Non-existent stores
- Concurrent operations (simulated)

### API Endpoint Tests

✅ **Functional Tests**
- All HTTP endpoints
- Request/response validation
- Status codes
- Response schemas

✅ **Integration Tests**
- DAO integration
- Configuration switching (JSON vs DynamoDB)
- OpenAPI documentation

✅ **Non-Functional Tests**
- Response format consistency
- Error message clarity
- Performance baseline

## Writing New Tests

### Test Naming Convention

Follow pytest naming conventions:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example: Adding a New DAO Test

```python
def test_new_feature(self, temp_json_file):
    """Test description here."""
    dao = InventoryDAOJson(temp_json_file)
    
    # Arrange
    expected_result = ...
    
    # Act
    actual_result = dao.some_method()
    
    # Assert
    assert actual_result == expected_result
```

### Example: Adding a New API Test

```python
def test_new_endpoint(self, client, mock_json_mode):
    """Test description here."""
    response = client.get("/new-endpoint")
    
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

## Fixtures

Common fixtures available in tests:

- `client` - FastAPI TestClient
- `temp_json_file` - Temporary JSON file with sample data
- `empty_json_file` - Empty JSON file
- `mock_json_mode` - Mock inventory service in JSON mode
- `sample_inventory_data` - Sample inventory data dict
- `mock_dynamodb_table` - Mocked DynamoDB table with test data

## Continuous Integration

These tests are designed to run in CI/CD pipelines. Example GitHub Actions workflow:

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest -v --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Import Errors

If you see import errors, make sure you're in the correct directory:

```bash
cd inventory_api
pytest
```

Or set PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Moto DynamoDB Issues

If DynamoDB mocking fails, ensure moto is properly installed:

```bash
pip install --upgrade moto[dynamodb]
```

### Test Data Conflicts

Tests use temporary files and mocked services to avoid conflicts. If you encounter data conflicts, ensure:
- Temporary files are being cleaned up
- Each test uses isolated fixtures
- No global state is being modified

## Best Practices

1. **Use Fixtures**: Reuse setup code with pytest fixtures
2. **Isolate Tests**: Each test should be independent
3. **Clear Assertions**: Use descriptive assertion messages
4. **Test Edge Cases**: Don't just test the happy path
5. **Mock External Services**: Use moto for AWS, temporary files for JSON
6. **Document Tests**: Add docstrings explaining what each test validates

## Performance

Expected test execution times:
- Full test suite: ~5-10 seconds
- DAO tests only: ~2-3 seconds
- API tests only: ~2-3 seconds

If tests are slower, consider:
- Using markers to skip slow tests during development
- Optimizing fixture setup/teardown
- Running tests in parallel with `pytest-xdist`

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [Moto Documentation](https://docs.getmoto.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/latest/explanation/goodpractices.html)
