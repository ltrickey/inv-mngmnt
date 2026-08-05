"""
Configuration module for the Inventory API.
Handles environment variables and path configuration.
"""
import os
import sys
from pathlib import Path

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading


# File paths.
# Locally, config.py lives at inventory_api/config.py (repo root is one level up).
# In Docker, it's copied flat to /app/config.py alongside seed_data/ and catalog/
# (both mounted/copied directly into /app), so the repo root *is* this file's dir.
_THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _THIS_DIR if (_THIS_DIR / "seed_data").is_dir() else _THIS_DIR.parent
PRODUCTS_BY_STORE_FILE = PROJECT_ROOT / "seed_data" / "products_by_store.json"

# So the top-level `catalog` package (shared table-naming helper) can be
# imported from here, whether run in Docker or directly from inventory_api/.
sys.path.insert(0, str(PROJECT_ROOT))
from catalog.dynamo import derive_table_name

# Environment configuration
USE_DYNAMODB = os.environ.get("USE_DYNAMODB", "").lower() in ("1", "true", "yes")
DYNAMODB_PRODUCTS_TABLE = os.environ.get("DYNAMODB_PRODUCTS_TABLE", "").strip()
NAME_PREFIX = os.environ.get("NAME_PREFIX", "").strip()

if not DYNAMODB_PRODUCTS_TABLE and NAME_PREFIX:
    DYNAMODB_PRODUCTS_TABLE = f"{NAME_PREFIX}-products"

PRODUCTS_BY_STORE_TABLE = derive_table_name(DYNAMODB_PRODUCTS_TABLE, "-products_by_store")
SALES_EVENTS_TABLE = derive_table_name(DYNAMODB_PRODUCTS_TABLE, "-sales_events")
