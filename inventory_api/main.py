from typing import List

from fastapi import FastAPI

from inventory import get_inventory_DAO, InventoryItem, getMode



app = FastAPI(
    title="Inventory Service",
    description="Inventory API backed by DynamoDB products_by_store table.",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": getMode(),
    }


@app.get("/inventory/{store_id}")
def list_inventory_for_store(store_id: str) -> List[InventoryItem]:
    """
    Return all inventory rows for a given store_id.
    - When USE_DYNAMODB=1 and PRODUCTS_BY_STORE_TABLE is set, read from DynamoDB.
    - Otherwise, read from local seed_data/products_by_store.json.
    """
    return get_inventory_DAO().get_all_by_store_id(store_id)


@app.get("/inventory/{store_id}/{barcode}")
def get_inventory_item(store_id: str, barcode: str) -> InventoryItem:
    """
    Return a single inventory row for (store_id, barcode) or 404 if not found.
    """
    return get_inventory_DAO().get_by_store_id_and_barcode(store_id, barcode)
