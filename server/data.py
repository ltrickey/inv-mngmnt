"""
Data access layer: load stores, stock, and sales from DynamoDB (EC2) or JSON (local).
Table names are derived from DYNAMODB_PRODUCTS_TABLE when USE_DYNAMODB is set.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

USE_DYNAMODB = os.environ.get('USE_DYNAMODB', '').lower() in ('1', 'true', 'yes')
DYNAMODB_PRODUCTS_TABLE = os.environ.get('DYNAMODB_PRODUCTS_TABLE', '').strip()

def _dynamodb_table_suffix(suffix):
    """Derive table name from products table (e.g. product-catalogue-test-products -> product-catalogue-test-stores)."""
    if not DYNAMODB_PRODUCTS_TABLE or not DYNAMODB_PRODUCTS_TABLE.endswith('-products'):
        return ''
    return DYNAMODB_PRODUCTS_TABLE[:-len('-products')] + suffix

DYNAMODB_STORES_TABLE = _dynamodb_table_suffix('-stores')
DYNAMODB_STOCK_TABLE = _dynamodb_table_suffix('-stock')
DYNAMODB_SALES_TABLE = _dynamodb_table_suffix('-sales')

_SEED_DIR = os.path.join(os.path.dirname(__file__), 'seed_data')
STORES_FILE = os.path.join(_SEED_DIR, 'stores.json')
STOCK_FILE = os.path.join(_SEED_DIR, 'stock.json')
SALES_FILE = os.path.join(_SEED_DIR, 'sales.json')


def _get_dynamodb_client():
    import boto3
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    return boto3.client('dynamodb', region_name=region) if region else boto3.client('dynamodb')


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


# --- Stock (PK barcode, SK store_id; GSI ByStore: hash store_id, range barcode) ---

def load_stock_from_json():
    try:
        with open(STOCK_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


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
    if not DYNAMODB_STOCK_TABLE:
        return []
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator('query')
        items = []
        for page in paginator.paginate(
            TableName=DYNAMODB_STOCK_TABLE,
            IndexName='ByStore',
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
    if not DYNAMODB_STOCK_TABLE:
        return None
    try:
        client = _get_dynamodb_client()
        resp = client.get_item(
            TableName=DYNAMODB_STOCK_TABLE,
            Key={'barcode': {'S': barcode}, 'store_id': {'S': store_id}}
        )
        item = resp.get('Item')
        return _deserialize_item(item) if item else None
    except Exception as e:
        logger.exception("DynamoDB get_stock_item failed: %s", e)
        return None


def get_stock_for_store(store_id):
    if USE_DYNAMODB and DYNAMODB_STOCK_TABLE:
        return get_stock_for_store_from_dynamodb(store_id)
    return get_stock_for_store_from_json(store_id)


def get_stock_item(store_id, barcode):
    if USE_DYNAMODB and DYNAMODB_STOCK_TABLE:
        return get_stock_item_from_dynamodb(store_id, barcode)
    return get_stock_item_from_json(store_id, barcode)


# --- Sales (PK store_id, SK barcode) ---

def load_sales_from_json():
    try:
        with open(SALES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_sales_for_store_from_json(store_id):
    rows = load_sales_from_json()
    return [r for r in rows if r.get('store_id') == store_id]


def get_sale_from_json(store_id, barcode):
    rows = load_sales_from_json()
    for r in rows:
        if r.get('store_id') == store_id and r.get('barcode') == barcode:
            return r
    return None


def get_sales_for_store_from_dynamodb(store_id):
    if not DYNAMODB_SALES_TABLE:
        return []
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator('query')
        items = []
        for page in paginator.paginate(
            TableName=DYNAMODB_SALES_TABLE,
            KeyConditionExpression='store_id = :sid',
            ExpressionAttributeValues={':sid': {'S': store_id}}
        ):
            for item in page.get('Items', []):
                items.append(_deserialize_item(item))
        return items
    except Exception as e:
        logger.exception("DynamoDB get_sales_for_store failed: %s", e)
        return []


def get_sale_from_dynamodb(store_id, barcode):
    if not DYNAMODB_SALES_TABLE:
        return None
    try:
        client = _get_dynamodb_client()
        resp = client.get_item(
            TableName=DYNAMODB_SALES_TABLE,
            Key={'store_id': {'S': store_id}, 'barcode': {'S': barcode}}
        )
        item = resp.get('Item')
        return _deserialize_item(item) if item else None
    except Exception as e:
        logger.exception("DynamoDB get_sale failed: %s", e)
        return None


def get_sales_for_store(store_id):
    if USE_DYNAMODB and DYNAMODB_SALES_TABLE:
        return get_sales_for_store_from_dynamodb(store_id)
    return get_sales_for_store_from_json(store_id)


def get_sale(store_id, barcode):
    if USE_DYNAMODB and DYNAMODB_SALES_TABLE:
        return get_sale_from_dynamodb(store_id, barcode)
    return get_sale_from_json(store_id, barcode)
