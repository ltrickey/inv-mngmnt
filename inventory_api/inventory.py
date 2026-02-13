from abc import abstractmethod
from typing import List, Optional

from pydantic import BaseModel
from fastapi import HTTPException
import json
import os
from pathlib import Path
import boto3
from boto3.dynamodb.types import TypeDeserializer

# TODO: Move this to a separate file?
class InventoryItem(BaseModel):
    store_id: str
    barcode: str
    quantity: int
    percent_off: int
    price: float


class InventoryDAO(InventoryItem):
    @abstractmethod
    def get_all_by_store_id(self, store_id: str) -> List[InventoryItem]:
        pass

    @abstractmethod
    def get_by_store_id_and_barcode(self, store_id: str, barcode: str) -> InventoryItem:
        pass

    # @abstractmethod
    # def deduct_quantity(self, store_id: str, barcode: str, quantity: int) -> bool:
    #     pass

    # # Deduct quantities of multiple products from a given store's inventory.  Return true if successfulf
    # @abstractmethod
    # def deduct_quantities(self, store_id: str, items: List[InventoryItem])-> bool:
    #     pass





USE_DYNAMODB = os.environ.get("USE_DYNAMODB", "").lower() in ("1", "true", "yes")
DYNAMODB_PRODUCTS_TABLE = os.environ.get("DYNAMODB_PRODUCTS_TABLE", "").strip()
NAME_PREFIX = os.environ.get("NAME_PREFIX", "").strip()

if not DYNAMODB_PRODUCTS_TABLE and NAME_PREFIX:
    DYNAMODB_PRODUCTS_TABLE = f"{NAME_PREFIX}-products"


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_BY_STORE_FILE = PROJECT_ROOT / "seed_data" / "products_by_store.json"


# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading


def _get_dynamodb_client():
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    return boto3.client("dynamodb", region_name=region) if region else boto3.client("dynamodb")

deserializer = TypeDeserializer()

def getMode():
    return "dynamodb" if USE_DYNAMODB else "json"

def _dynamodb_table_suffix(products_table: str, suffix: str) -> str:
    """
    Derive related table name from products table, mirroring server/data.py:
    e.g. product-catalogue-test-products -> product-catalogue-test-products_by_store
    """
    if not products_table or not products_table.endswith("-products"):
        return ""
    return products_table[: -len("-products")] + suffix

PRODUCTS_BY_STORE_TABLE = _dynamodb_table_suffix(DYNAMODB_PRODUCTS_TABLE, "-products_by_store")

DYNAMODB_CLIENT = _get_dynamodb_client()

def get_inventory_DAO() -> InventoryDAO:
    if USE_DYNAMODB and PRODUCTS_BY_STORE_TABLE and DYNAMODB_CLIENT:
        return InventoryDAODynamoDB(PRODUCTS_BY_STORE_TABLE, DYNAMODB_CLIENT)
    else:
        return InventoryDAOJson(PRODUCTS_BY_STORE_FILE)


def _deserialize_item(item: dict) -> dict:
    from decimal import Decimal

    raw = {k: deserializer.deserialize(v) for k, v in item.items()}
    result = {}
    for k, v in raw.items():
        if isinstance(v, Decimal):
            result[k] = float(v)
        elif isinstance(v, list):
            result[k] = [float(x) if isinstance(x, Decimal) else x for x in v]
        else:
            result[k] = v
    return result


# Abstract DAO Interface to decouple data access from business logic
#
#Using API Gateway, create an externally facing API that allows external clients to:

#check if a given store has at least a certain amount of a product in stock
#deduct a quantity of a given product from a given store's inventory

#deduct quantities of multiple products from a given store's inventory in one batch operation


# Concrete DAO for accessing inventory Data from DynamoDB
class InventoryDAODynamoDB(InventoryDAO):
    def __init__(self, table_name: str, client: boto3.client):
        self.table_name = table_name
        self.client = client

    def get_all_by_store_id(self, store_id: str) -> List[InventoryItem]:
        # DynamoDB mode
        try:
            paginator = self.client.get_paginator("query")
            items: List[dict] = []
            for page in paginator.paginate(
                TableName=PRODUCTS_BY_STORE_TABLE,
                KeyConditionExpression="store_id = :sid",
                ExpressionAttributeValues={":sid": {"S": store_id}},
            ):
                for item in page.get("Items", []):
                    items.append(_deserialize_item(item))
            return [InventoryItem(**item) for item in items]       
        except Exception as e:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail=f"DynamoDB query failed: {e}") from e

    def get_by_store_id_and_barcode(self, store_id: str, barcode: str) -> InventoryItem:
        try:
            
            resp = self.client.get_item(
                TableName=PRODUCTS_BY_STORE_TABLE,
                Key={"store_id": {"S": store_id}, "barcode": {"S": barcode}},
            )
            item = resp.get("Item")
            if not item:
                raise HTTPException(status_code=404, detail="Inventory item not found")
            return InventoryItem(**_deserialize_item(item)) 
        except HTTPException:
            raise
        except Exception as e:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail=f"DynamoDB get_item failed: {e}") from e



# Concrete DAO for accessing inventory Data from JSON file for local testing
class InventoryDAOJson(InventoryDAO):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_all_by_store_id(self, store_id: str) -> List[InventoryItem]:
        try:
            with PRODUCTS_BY_STORE_FILE.open("r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        return [InventoryItem(**r) for r in rows if r.get("store_id") == store_id]


    def get_by_store_id_and_barcode(self, store_id: str, barcode: str) -> InventoryItem:
        try:
            with PRODUCTS_BY_STORE_FILE.open("r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        for r in rows:
            if r.get("store_id") == store_id and r.get("barcode") == barcode:
                return InventoryItem(**r)
        raise HTTPException(status_code=404, detail="Inventory item not found")
