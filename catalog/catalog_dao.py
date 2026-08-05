"""
Data access for the catalog tables: products, stores, categories.
Reads from DynamoDB when USE_DYNAMODB is set, otherwise from JSON seed files.

This is the single owner of these three tables — currently only the customer
site's Flask app consumes it, but the tables themselves are core domain data,
not customer-site-specific, so the access layer lives at the repo root rather
than nested under customer_site/.
"""

import json
import logging
import os
import threading
import time

from catalog.dynamo import derive_table_name, deserialize_item

logger = logging.getLogger(__name__)

USE_DYNAMODB = os.environ.get("USE_DYNAMODB", "").lower() in ("1", "true", "yes")
DYNAMODB_PRODUCTS_TABLE = os.environ.get("DYNAMODB_PRODUCTS_TABLE", "").strip()
DYNAMODB_STORES_TABLE = derive_table_name(DYNAMODB_PRODUCTS_TABLE, "-stores")
DYNAMODB_CATEGORIES_TABLE = "categories"  # fixed name, not prefixed

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SEED_DIR = os.path.join(_REPO_ROOT, "seed_data")
STORES_FILE = os.path.join(_SEED_DIR, "stores.json")
PRODUCTS_FILE = os.path.join(_SEED_DIR, "products.json")

# ---------------------------------------------------------------------------
# Simple TTL cache – avoids repeated DynamoDB scans
# ---------------------------------------------------------------------------
CACHE_TTL_SECONDS = 120  # catalog data rarely changes; 2 minutes is safe

_cache = {}
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL_SECONDS:
            return entry["data"]
    return None


def _cache_set(key, data):
    with _cache_lock:
        _cache[key] = {"data": data, "ts": time.time()}


_dynamodb_client = None


def _get_dynamodb_client():
    global _dynamodb_client
    if _dynamodb_client is None:
        import boto3
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        _dynamodb_client = boto3.client("dynamodb", region_name=region) if region else boto3.client("dynamodb")
    return _dynamodb_client


# --- Stores ---

def load_stores_from_json():
    try:
        with open(STORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_stores_from_dynamodb():
    if not DYNAMODB_STORES_TABLE:
        return []
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator("scan")
        stores = []
        for page in paginator.paginate(TableName=DYNAMODB_STORES_TABLE):
            for item in page.get("Items", []):
                stores.append(deserialize_item(item))
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
            Key={"store_id": {"S": store_id}},
        )
        item = resp.get("Item")
        return deserialize_item(item) if item else None
    except Exception as e:
        logger.exception("DynamoDB get_store failed: %s", e)
        return None


def get_store_from_json(store_id):
    stores = load_stores_from_json()
    for s in stores:
        if s.get("store_id") == store_id:
            return s
    return None


def get_store(store_id):
    if USE_DYNAMODB and DYNAMODB_STORES_TABLE:
        return get_store_from_dynamodb(store_id)
    return get_store_from_json(store_id)


# --- Categories ---

def load_categories_from_dynamodb():
    if not DYNAMODB_CATEGORIES_TABLE:
        return []
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator("scan")
        items = []
        for page in paginator.paginate(TableName=DYNAMODB_CATEGORIES_TABLE):
            for item in page.get("Items", []):
                items.append(deserialize_item(item))
        return items
    except Exception as e:
        logger.exception("DynamoDB load_categories failed: %s", e)
        return []


# --- Products ---

def load_products_from_json():
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_products_from_dynamodb():
    if not DYNAMODB_PRODUCTS_TABLE:
        return []
    cached = _cache_get("all_products_dynamo")
    if cached is not None:
        return cached
    try:
        client = _get_dynamodb_client()
        paginator = client.get_paginator("scan")
        products = []
        for page in paginator.paginate(TableName=DYNAMODB_PRODUCTS_TABLE):
            for item in page.get("Items", []):
                products.append(deserialize_item(item))
        _cache_set("all_products_dynamo", products)
        return products
    except Exception as e:
        logger.exception("DynamoDB load_products failed: %s", e)
        return []


def load_products():
    """
    Load raw products from DynamoDB or JSON, cached. Callers are responsible
    for any presentation-layer transforms (e.g. resolving image URLs).
    """
    cached = _cache_get("all_products")
    if cached is not None:
        return cached
    if USE_DYNAMODB and DYNAMODB_PRODUCTS_TABLE:
        products = load_products_from_dynamodb()
    else:
        products = load_products_from_json()
    _cache_set("all_products", products)
    return products


def get_products_by_category_filters_dynamodb(p_category=None, s_category=None, t_category=None):
    """
    Get products matching category filters using GSI_Category (primary_category, category_path).
    category_path format: "secondary#tertiary#barcode" (e.g. "Milk#NONE#0123456789012").
    """
    if not DYNAMODB_PRODUCTS_TABLE:
        return []
    p_val = str(p_category).strip() if p_category else None
    s_val = str(s_category).strip() if s_category else None
    t_val = str(t_category).strip() if t_category else None
    if not p_val and not s_val and not t_val:
        return []
    cache_key = f"cat_filter:{p_val}:{s_val}:{t_val}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        client = _get_dynamodb_client()
        items = []

        if p_val:
            # Query GSI_Category by primary_category; optionally filter by category_path prefix
            key_condition = "primary_category = :p"
            expr_vals = {":p": {"S": p_val}}
            filter_expr = None
            if t_val and s_val:
                filter_expr = "begins_with(category_path, :prefix)"
                expr_vals[":prefix"] = {"S": s_val + "#" + t_val + "#"}
            elif s_val:
                filter_expr = "begins_with(category_path, :prefix)"
                expr_vals[":prefix"] = {"S": s_val + "#"}
            elif t_val:
                # Tertiary only: category_path contains "#t_val#"
                filter_expr = "contains(category_path, :ter)"
                expr_vals[":ter"] = {"S": "#" + t_val + "#"}

            paginator = client.get_paginator("query")
            paginate_kw = {
                "TableName": DYNAMODB_PRODUCTS_TABLE,
                "IndexName": "GSI_Category",
                "KeyConditionExpression": key_condition,
                "ExpressionAttributeValues": expr_vals,
            }
            if filter_expr:
                paginate_kw["FilterExpression"] = filter_expr
            for page in paginator.paginate(**paginate_kw):
                for item in page.get("Items", []):
                    items.append(deserialize_item(item))
        else:
            # Secondary or tertiary only (no primary): scan with filter
            filter_parts = []
            expr_vals = {}
            if s_val:
                filter_parts.append("begins_with(category_path, :sec)")
                expr_vals[":sec"] = {"S": s_val + "#"}
            if t_val:
                filter_parts.append("contains(category_path, :ter)")
                expr_vals[":ter"] = {"S": "#" + t_val + "#"}
            if not expr_vals:
                return []
            paginator = client.get_paginator("scan")
            for page in paginator.paginate(
                TableName=DYNAMODB_PRODUCTS_TABLE,
                FilterExpression=" AND ".join(filter_parts),
                ExpressionAttributeValues=expr_vals,
            ):
                for item in page.get("Items", []):
                    items.append(deserialize_item(item))

        _cache_set(cache_key, items)
        return items
    except Exception as e:
        logger.exception("DynamoDB get_products_by_category_filters failed: %s", e)
        return []
