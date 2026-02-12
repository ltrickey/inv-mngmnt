from typing import List

import os
from pathlib import Path
from fastapi import FastAPI
from inventory import InventoryDAODynamoDB, InventoryDAOJson, InventoryItem

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading


def _dynamodb_table_suffix(products_table: str, suffix: str) -> str:
    """
    Derive related table name from products table, mirroring server/data.py:
    e.g. product-catalogue-test-products -> product-catalogue-test-products_by_store
    """
    if not products_table or not products_table.endswith("-products"):
        return ""
    return products_table[: -len("-products")] + suffix



#TOOD: Figure out best place to unify this logic between here and inventory.py
USE_DYNAMODB = os.environ.get("USE_DYNAMODB", "").lower() in ("1", "true", "yes")
DYNAMODB_PRODUCTS_TABLE = os.environ.get("DYNAMODB_PRODUCTS_TABLE", "").strip()
NAME_PREFIX = os.environ.get("NAME_PREFIX", "").strip()

if not DYNAMODB_PRODUCTS_TABLE and NAME_PREFIX:
    DYNAMODB_PRODUCTS_TABLE = f"{NAME_PREFIX}-products"

PRODUCTS_BY_STORE_TABLE = _dynamodb_table_suffix(DYNAMODB_PRODUCTS_TABLE, "-products_by_store")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_BY_STORE_FILE = PROJECT_ROOT / "seed_data" / "products_by_store.json"



app = FastAPI(
    title="Inventory Service",
    description="Inventory API backed by DynamoDB products_by_store table.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "dynamodb" if (USE_DYNAMODB and PRODUCTS_BY_STORE_TABLE) else "json",
        "products_table": DYNAMODB_PRODUCTS_TABLE or None,
        "products_by_store_table": PRODUCTS_BY_STORE_TABLE or None,
    }


@app.get("/inventory/{store_id}")
def list_inventory_for_store(store_id: str) -> List[InventoryItem]:
    """
    Return all inventory rows for a given store_id.
    - When USE_DYNAMODB=1 and PRODUCTS_BY_STORE_TABLE is set, read from DynamoDB.
    - Otherwise, read from local seed_data/products_by_store.json.
    """
    # Local / dev mode: JSON file
    if not USE_DYNAMODB or not PRODUCTS_BY_STORE_TABLE:
        return InventoryDAOJson(PRODUCTS_BY_STORE_FILE).get_all_by_store_id(store_id)
    else:   
        return InventoryDAODynamoDB(PRODUCTS_BY_STORE_TABLE).get_all_by_store_id(store_id)



@app.get("/inventory/{store_id}/{barcode}")
def get_inventory_item(store_id: str, barcode: str) -> InventoryItem:
    """
    Return a single inventory row for (store_id, barcode) or 404 if not found.
    """
    # Local / dev mode: JSON file
    if not USE_DYNAMODB or not PRODUCTS_BY_STORE_TABLE:
        return InventoryDAOJson(PRODUCTS_BY_STORE_FILE).get_by_store_id_and_barcode(store_id, barcode)
    # DynamoDB mode
    else:
        return InventoryDAODynamoDB(PRODUCTS_BY_STORE_TABLE).get_by_store_id_and_barcode(store_id, barcode)
