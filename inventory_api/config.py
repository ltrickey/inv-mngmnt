"""
Configuration module for the Inventory API.
Handles environment variables and path configuration.
"""
import os
from pathlib import Path

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading


# Environment configuration
USE_DYNAMODB = os.environ.get("USE_DYNAMODB", "").lower() in ("1", "true", "yes")
DYNAMODB_PRODUCTS_TABLE = os.environ.get("DYNAMODB_PRODUCTS_TABLE", "").strip()
NAME_PREFIX = os.environ.get("NAME_PREFIX", "").strip()

if not DYNAMODB_PRODUCTS_TABLE and NAME_PREFIX:
    DYNAMODB_PRODUCTS_TABLE = f"{NAME_PREFIX}-products"


# File paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_BY_STORE_FILE = PROJECT_ROOT / "seed_data" / "products_by_store.json"


def _dynamodb_table_suffix(products_table: str, suffix: str) -> str:
    """
    Derive related table name from products table, mirroring server/data.py:
    e.g. product-catalogue-test-products -> product-catalogue-test-products_by_store
    """
    if not products_table or not products_table.endswith("-products"):
        return ""
    return products_table[: -len("-products")] + suffix


PRODUCTS_BY_STORE_TABLE = _dynamodb_table_suffix(DYNAMODB_PRODUCTS_TABLE, "-products_by_store")
SALES_EVENTS_TABLE = _dynamodb_table_suffix(DYNAMODB_PRODUCTS_TABLE, "-sales_events")
