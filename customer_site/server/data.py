"""
Stock/sales data access: proxy to the FastAPI inventory service (the sole
owner of products_by_store), falling back to local JSON seed data only when
the inventory API isn't configured — i.e. local dev without Docker Compose.

There is deliberately no direct-DynamoDB path here: products_by_store is
inventory_api's table, and duplicating its DAO here previously meant two
independent implementations of the same reads could silently drift.
"""

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

INVENTORY_API_BASE_URL = os.environ.get('INVENTORY_API_BASE_URL', '').rstrip('/') or ''

# Resolve repo root: works both in Docker (/app/) and locally
# (customer_site/server/ -> grandparent has seed_data)
_PARENT = os.path.dirname(os.path.dirname(__file__))
_REPO_ROOT = _PARENT if os.path.isdir(os.path.join(_PARENT, 'seed_data')) else os.path.dirname(_PARENT)
_SEED_DIR = os.path.join(_REPO_ROOT, 'seed_data')
PRODUCTS_BY_STORE_FILE = os.path.join(_SEED_DIR, 'products_by_store.json')


def _inventory_api_get(path: str):
    """Call the inventory API if configured. Returns JSON on success, None on failure/disabled."""
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


# --- Products by store (stock + sale price per store; local JSON fallback only) ---

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


def get_stock_for_store(store_id):
    data = _inventory_api_get(f"/inventory/{store_id}")
    if data is not None:
        return data
    return get_stock_for_store_from_json(store_id)


def get_stock_item(store_id, barcode):
    data = _inventory_api_get(f"/inventory/{store_id}/{barcode}")
    if data is not None:
        return data
    return get_stock_item_from_json(store_id, barcode)


# --- Sales (derived from products_by_store: items with percent_off > 0) ---

def get_sales_for_store_from_json(store_id):
    rows = _load_products_by_store_from_json()
    return [r for r in rows if r.get('store_id') == store_id and (r.get('percent_off') or 0) > 0]


def get_sale_from_json(store_id, barcode):
    rows = _load_products_by_store_from_json()
    for r in rows:
        if r.get('store_id') == store_id and r.get('barcode') == barcode and (r.get('percent_off') or 0) > 0:
            return r
    return None


def get_sales_for_store(store_id):
    data = _inventory_api_get(f"/inventory/{store_id}")
    if data is not None:
        return [r for r in data if (r.get('percent_off') or 0) > 0]
    return get_sales_for_store_from_json(store_id)


def get_sale(store_id, barcode):
    data = _inventory_api_get(f"/inventory/{store_id}/{barcode}")
    if data is not None:
        return data if (data.get('percent_off') or 0) > 0 else None
    return get_sale_from_json(store_id, barcode)
