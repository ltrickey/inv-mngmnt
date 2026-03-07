# Inventory API Testing

## Setup

```bash
cd inventory_api
pip install -r requirements.txt
```

## Running Tests

```bash
# All tests
pytest

# Verbose
pytest -v

# Specific file
pytest tests/test_inventory_dao.py
pytest tests/test_main.py

# With coverage
pytest --cov=. --cov-report=term
```

## Test Structure

```
tests/
├── conftest.py            # Adds parent directory to sys.path
├── test_inventory_dao.py  # InventoryDAOJson and InventoryDAODynamoDB tests (uses moto)
└── test_main.py           # FastAPI endpoint integration tests
```

### test_inventory_dao.py

- `TestInventoryDAOJson` — CRUD, quantity deduction, atomicity, error handling against local JSON
- `TestInventoryDAODynamoDB` — same tests with mocked DynamoDB via `moto`
- `TestInventoryItemModel` — Pydantic model validation

### test_main.py

- Health endpoint
- `GET /api/inventory/{store_id}` and `GET /api/inventory/{store_id}/{barcode}`
- Error scenarios (404, 400 insufficient stock)
- DAO integration (JSON vs DynamoDB mode)

## Troubleshooting

If you see import errors, run pytest from the `inventory_api/` directory (not the repo root):

```bash
cd inventory_api
pytest
```
