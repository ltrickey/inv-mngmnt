from typing import List

import json
import os
from pathlib import Path

import boto3
from boto3.dynamodb.types import TypeDeserializer
from fastapi import FastAPI, HTTPException

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading


def _get_dynamodb_client():
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    return boto3.client("dynamodb", region_name=region) if region else boto3.client("dynamodb")


def _dynamodb_table_suffix(products_table: str, suffix: str) -> str:
    """
    Derive related table name from products table, mirroring server/data.py:
    e.g. product-catalogue-test-products -> product-catalogue-test-products_by_store
    """
    if not products_table or not products_table.endswith("-products"):
        return ""
    return products_table[: -len("-products")] + suffix


USE_DYNAMODB = os.environ.get("USE_DYNAMODB", "").lower() in ("1", "true", "yes")
DYNAMODB_PRODUCTS_TABLE = os.environ.get("DYNAMODB_PRODUCTS_TABLE", "").strip()
NAME_PREFIX = os.environ.get("NAME_PREFIX", "").strip()

if not DYNAMODB_PRODUCTS_TABLE and NAME_PREFIX:
    DYNAMODB_PRODUCTS_TABLE = f"{NAME_PREFIX}-products"

PRODUCTS_BY_STORE_TABLE = _dynamodb_table_suffix(DYNAMODB_PRODUCTS_TABLE, "-products_by_store")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_BY_STORE_FILE = PROJECT_ROOT / "seed_data" / "products_by_store.json"

deserializer = TypeDeserializer()


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
def list_inventory_for_store(store_id: str):
    """
    Return all inventory rows for a given store_id.
    - When USE_DYNAMODB=1 and PRODUCTS_BY_STORE_TABLE is set, read from DynamoDB.
    - Otherwise, read from local seed_data/products_by_store.json.
    """
    # Local / dev mode: JSON file
    if not USE_DYNAMODB or not PRODUCTS_BY_STORE_TABLE:
        try:
            with PRODUCTS_BY_STORE_FILE.open("r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        return [r for r in rows if r.get("store_id") == store_id]

    # DynamoDB mode
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator("query")
        items: List[dict] = []
        for page in paginator.paginate(
            TableName=PRODUCTS_BY_STORE_TABLE,
            KeyConditionExpression="store_id = :sid",
            ExpressionAttributeValues={":sid": {"S": store_id}},
        ):
            for item in page.get("Items", []):
                items.append(_deserialize_item(item))
        return items
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"DynamoDB query failed: {e}") from e


@app.get("/inventory/{store_id}/{barcode}")
def get_inventory_item(store_id: str, barcode: str):
    """
    Return a single inventory row for (store_id, barcode) or 404 if not found.
    """
    # Local / dev mode: JSON file
    if not USE_DYNAMODB or not PRODUCTS_BY_STORE_TABLE:
        try:
            with PRODUCTS_BY_STORE_FILE.open("r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        for r in rows:
            if r.get("store_id") == store_id and r.get("barcode") == barcode:
                return r
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # DynamoDB mode
    try:
        client = _get_dynamodb_client()
        resp = client.get_item(
            TableName=PRODUCTS_BY_STORE_TABLE,
            Key={"store_id": {"S": store_id}, "barcode": {"S": barcode}},
        )
        item = resp.get("Item")
        if not item:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        return _deserialize_item(item)
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"DynamoDB get_item failed: {e}") from e

