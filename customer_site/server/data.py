"""
Data access layer: load stores, stock, and sales from DynamoDB (EC2) or JSON (local).
Table names are derived from DYNAMODB_PRODUCTS_TABLE when USE_DYNAMODB is set.
"""

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

USE_DYNAMODB = os.environ.get('USE_DYNAMODB', '').lower() in ('1', 'true', 'yes')
DYNAMODB_PRODUCTS_TABLE = os.environ.get('DYNAMODB_PRODUCTS_TABLE', '').strip()
INVENTORY_API_BASE_URL = os.environ.get('INVENTORY_API_BASE_URL', '').rstrip('/') or ''

def _dynamodb_table_suffix(suffix):
    """Derive table name from products table (e.g. product-catalogue-test-products -> product-catalogue-test-stores)."""
    if not DYNAMODB_PRODUCTS_TABLE or not DYNAMODB_PRODUCTS_TABLE.endswith('-products'):
        return ''
    return DYNAMODB_PRODUCTS_TABLE[:-len('-products')] + suffix

DYNAMODB_STORES_TABLE = _dynamodb_table_suffix('-stores')
DYNAMODB_PRODUCTS_BY_STORE_TABLE = _dynamodb_table_suffix('-products_by_store')
DYNAMODB_CATEGORIES_TABLE = 'categories'  # fixed name, not prefixed

# Resolve repo root: works both on EC2 (/opt/product_catalogue/server/ -> parent has seed_data)
# and locally (customer_site/server/ -> grandparent has seed_data)
_PARENT = os.path.dirname(os.path.dirname(__file__))
_REPO_ROOT = _PARENT if os.path.isdir(os.path.join(_PARENT, 'seed_data')) else os.path.dirname(_PARENT)
_SEED_DIR = os.path.join(_REPO_ROOT, 'seed_data')
STORES_FILE = os.path.join(_SEED_DIR, 'stores.json')
PRODUCTS_BY_STORE_FILE = os.path.join(_SEED_DIR, 'products_by_store.json')


def _get_dynamodb_client():
    import boto3
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    return boto3.client('dynamodb', region_name=region) if region else boto3.client('dynamodb')


def _inventory_api_get(path: str):
    """Call external inventory API if configured. Returns JSON on success, None on failure/disabled."""
    if not INVENTORY_API_BASE_URL:
        return None
    url = f"{INVENTORY_API_BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.exception("Inventory API request failed for %s: %s", url, e)
        return None


def _deserialize_item(item):
    from boto3.dynamodb.types import TypeDeserializer
    from decimal import Decimal
    deserializer = TypeDeserializer()
    raw = {k: deserializer.deserialize(v) for k, v in item.items()}
    # Convert Decimal to float for JSON
    result = {}
    for k, v in raw.items():
        if isinstance(v, Decimal):
            result[k] = float(v)
        elif isinstance(v, list):
            result[k] = [float(x) if isinstance(x, Decimal) else x for x in v]
        else:
            result[k] = v
    return result


# --- Stores ---

def load_stores_from_json():
    try:
        with open(STORES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_stores_from_dynamodb():
    if not DYNAMODB_STORES_TABLE:
        return []
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator('scan')
        stores = []
        for page in paginator.paginate(TableName=DYNAMODB_STORES_TABLE):
            for item in page.get('Items', []):
                stores.append(_deserialize_item(item))
        return stores
    except Exception as e:
        logger.exception("DynamoDB load_stores failed: %s", e)
        return []


def get_all_stores():
    if USE_DYNAMODB and DYNAMODB_STORES_TABLE:
        return load_stores_from_dynamodb()
    return load_stores_from_json()


def get_store_from_dynamodb(store_id):
    if not DYNAMODB_STORES_TABLE:
        return None
    try:
        client = _get_dynamodb_client()
        resp = client.get_item(
            TableName=DYNAMODB_STORES_TABLE,
            Key={'store_id': {'S': store_id}}
        )
        item = resp.get('Item')
        return _deserialize_item(item) if item else None
    except Exception as e:
        logger.exception("DynamoDB get_store failed: %s", e)
        return None


def get_store_from_json(store_id):
    stores = load_stores_from_json()
    for s in stores:
        if s.get('store_id') == store_id:
            return s
    return None


def get_store(store_id):
    if USE_DYNAMODB and DYNAMODB_STORES_TABLE:
        return get_store_from_dynamodb(store_id)
    return get_store_from_json(store_id)


# --- Products by store (stock + sale price per store; PK barcode, SK store_id; GSI ByStore) ---

def _load_products_by_store_from_json():
    try:
        with open(PRODUCTS_BY_STORE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_stock_from_json():
    return _load_products_by_store_from_json()


def get_stock_for_store_from_json(store_id):
    rows = load_stock_from_json()
    return [r for r in rows if r.get('store_id') == store_id]


def get_stock_item_from_json(store_id, barcode):
    rows = load_stock_from_json()
    for r in rows:
        if r.get('store_id') == store_id and r.get('barcode') == barcode:
            return r
    return None


def get_stock_for_store_from_dynamodb(store_id):
    if not DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return []
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator('query')
        items = []
        for page in paginator.paginate(
            TableName=DYNAMODB_PRODUCTS_BY_STORE_TABLE,
            KeyConditionExpression='store_id = :sid',
            ExpressionAttributeValues={':sid': {'S': store_id}}
        ):
            for item in page.get('Items', []):
                items.append(_deserialize_item(item))
        return items
    except Exception as e:
        logger.exception("DynamoDB get_stock_for_store failed: %s", e)
        return []


def get_stock_item_from_dynamodb(store_id, barcode):
    if not DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return None
    try:
        client = _get_dynamodb_client()
        resp = client.get_item(
            TableName=DYNAMODB_PRODUCTS_BY_STORE_TABLE,
            Key={'store_id': {'S': store_id}, 'barcode': {'S': barcode}}
        )
        item = resp.get('Item')
        return _deserialize_item(item) if item else None
    except Exception as e:
        logger.exception("DynamoDB get_stock_item failed: %s", e)
        return None


def get_stock_for_store(store_id):
    # Prefer external inventory API if configured
    data = _inventory_api_get(f"/inventory/{store_id}")
    if data is not None:
        return data
    if USE_DYNAMODB and DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return get_stock_for_store_from_dynamodb(store_id)
    return get_stock_for_store_from_json(store_id)


def get_stock_item(store_id, barcode):
    data = _inventory_api_get(f"/inventory/{store_id}/{barcode}")
    if data is not None:
        return data
    if USE_DYNAMODB and DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return get_stock_item_from_dynamodb(store_id, barcode)
    return get_stock_item_from_json(store_id, barcode)


# --- Sales (derived from products_by_store: items with percent_off > 0) ---

def load_sales_from_json():
    rows = _load_products_by_store_from_json()
    return [r for r in rows if (r.get('percent_off') or 0) > 0]


def get_sales_for_store_from_json(store_id):
    rows = _load_products_by_store_from_json()
    return [r for r in rows if r.get('store_id') == store_id and (r.get('percent_off') or 0) > 0]


def get_sale_from_json(store_id, barcode):
    rows = _load_products_by_store_from_json()
    for r in rows:
        if r.get('store_id') == store_id and r.get('barcode') == barcode and (r.get('percent_off') or 0) > 0:
            return r
    return None


def get_sales_for_store_from_dynamodb(store_id):
    """Sales = products_by_store rows for this store with percent_off > 0."""
    if not DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return []
    try:
        items = get_stock_for_store_from_dynamodb(store_id)
        return [r for r in items if (r.get('percent_off') or 0) > 0]
    except Exception as e:
        logger.exception("DynamoDB get_sales_for_store failed: %s", e)
        return []


def get_sale_from_dynamodb(store_id, barcode):
    if not DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return None
    try:
        item = get_stock_item_from_dynamodb(store_id, barcode)
        return item if item and (item.get('percent_off') or 0) > 0 else None
    except Exception as e:
        logger.exception("DynamoDB get_sale failed: %s", e)
        return None


def get_sales_for_store(store_id):
    data = _inventory_api_get(f"/inventory/{store_id}")
    if data is not None:
        return [r for r in data if (r.get('percent_off') or 0) > 0]
    if USE_DYNAMODB and DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return get_sales_for_store_from_dynamodb(store_id)
    return get_sales_for_store_from_json(store_id)


def get_sale(store_id, barcode):
    data = _inventory_api_get(f"/inventory/{store_id}/{barcode}")
    if data is not None:
        print(data)
        return data if (data.get('percent_off') or 0) > 0 else None
    if USE_DYNAMODB and DYNAMODB_PRODUCTS_BY_STORE_TABLE:
        return get_sale_from_dynamodb(store_id, barcode)
    return get_sale_from_json(store_id, barcode)


# --- Categories (from categories table when using DynamoDB) ---

def load_categories_from_json():
    """Categories are derived from products in JSON mode; see app.get_categories."""
    return []


def load_categories_from_dynamodb():
    if not DYNAMODB_CATEGORIES_TABLE:
        return []
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator('scan')
        items = []
        for page in paginator.paginate(TableName=DYNAMODB_CATEGORIES_TABLE):
            for item in page.get('Items', []):
                items.append(_deserialize_item(item))
        return items
    except Exception as e:
        logger.exception("DynamoDB load_categories failed: %s", e)
        return []
