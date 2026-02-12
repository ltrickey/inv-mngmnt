from typing import List, Optional

import os

import boto3
from boto3.dynamodb.types import TypeDeserializer
from fastapi import FastAPI, HTTPException


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


DYNAMODB_PRODUCTS_TABLE = os.environ.get("DYNAMODB_PRODUCTS_TABLE", "").strip()
NAME_PREFIX = os.environ.get("NAME_PREFIX", "").strip()

if not DYNAMODB_PRODUCTS_TABLE and NAME_PREFIX:
    DYNAMODB_PRODUCTS_TABLE = f"{NAME_PREFIX}-products"

PRODUCTS_BY_STORE_TABLE = _dynamodb_table_suffix(DYNAMODB_PRODUCTS_TABLE, "-products_by_store")

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
        "products_table": DYNAMODB_PRODUCTS_TABLE or None,
        "products_by_store_table": PRODUCTS_BY_STORE_TABLE or None,
    }


@app.get("/inventory/{store_id}")
def list_inventory_for_store(store_id: str):
    """
    Return all inventory rows for a given store_id from the products_by_store table.
    """
    if not PRODUCTS_BY_STORE_TABLE:
        raise HTTPException(status_code=500, detail="PRODUCTS_BY_STORE_TABLE not configured")

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
    if not PRODUCTS_BY_STORE_TABLE:
        raise HTTPException(status_code=500, detail="PRODUCTS_BY_STORE_TABLE not configured")

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

