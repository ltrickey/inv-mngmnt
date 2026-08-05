import sys
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging
import os

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resolve repo root for local dev paths (infrastructure/images) and so the
# top-level `catalog` package (products/stores/categories data access,
# shared conceptually across services) can be imported from here.
_PARENT = os.path.dirname(os.path.dirname(__file__))
_PROJECT_ROOT = _PARENT if os.path.isdir(os.path.join(_PARENT, 'seed_data')) else os.path.dirname(_PARENT)
sys.path.insert(0, _PROJECT_ROOT)

from catalog.catalog_dao import (
    USE_DYNAMODB,
    DYNAMODB_PRODUCTS_TABLE,
    load_products as _load_catalog_products,
    get_products_by_category_filters_dynamodb,
    load_categories_from_dynamodb,
)

app = Flask(__name__)
CORS(app)

# Register blueprints for stores, stock, sales.
# Stock and sales endpoints proxy to the FastAPI inventory service when INVENTORY_API_BASE_URL is set.
from stores import stores_bp
from stock import stock_bp
from sales import sales_bp
app.register_blueprint(stores_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(sales_bp)

# Serve static images from infrastructure/images directory
IMAGES_DIR = os.path.join(_PROJECT_ROOT, 'infrastructure', 'images')
PLACEHOLDER_IMAGE = 'placeholder.png'

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from infrastructure/images directory; fallback to placeholder if missing."""
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.isfile(path):
        filename = PLACEHOLDER_IMAGE
    return send_from_directory(IMAGES_DIR, filename)

# S3 configuration (optional - if not set, uses local images)
# S3_BUCKET_URL is the public base URL (e.g. https://bucket.s3.amazonaws.com)
S3_BUCKET_URL = os.environ.get('S3_BUCKET_URL', '').rstrip('/')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', None)


def get_image_url(image_path):
    """
    Get the full image URL based on environment configuration.
    If S3_BUCKET_URL is set, returns a direct public S3 URL (no signing needed).
    Otherwise, returns a Flask-served URL for local testing.
    """
    if S3_BUCKET_URL:
        s3_path = image_path.replace('infrastructure/', '') if image_path.startswith('infrastructure/') else image_path
        return f"{S3_BUCKET_URL}/{s3_path}"
    else:
        if image_path.startswith(('http://', 'https://')):
            return image_path
        filename = os.path.basename(image_path)
        if filename and not os.path.isfile(os.path.join(IMAGES_DIR, filename)):
            filename = PLACEHOLDER_IMAGE
        return f"/images/{filename}"


def load_products():
    """
    Load catalog products (DynamoDB or JSON, cached by catalog_dao) and resolve
    image URLs for this site's presentation (S3 vs local /images route).
    """
    products = []
    for product in _load_catalog_products():
        product = dict(product)
        if product.get('image_url'):
            product['image_url'] = get_image_url(product['image_url'])
        products.append(product)
    return products


@app.route('/debug', methods=['GET'])
def debug():
    """
    Diagnostics: data source, table name, product count, and any DynamoDB error.
    Safe to expose (no secrets). Use to verify DynamoDB is configured and working.
    """
    info = {
        'data_source': 'dynamodb' if (USE_DYNAMODB and DYNAMODB_PRODUCTS_TABLE) else 'json',
        'dynamodb_table_configured': bool(DYNAMODB_PRODUCTS_TABLE),
        'use_dynamodb_env': USE_DYNAMODB,
    }
    try:
        products = load_products()
        info['product_count'] = len(products)
    except Exception as e:
        info['error'] = str(e)
        info['product_count'] = 0
    # Don't expose full table name in logs; last segment is enough for debugging
    if DYNAMODB_PRODUCTS_TABLE:
        info['table_name'] = DYNAMODB_PRODUCTS_TABLE.split('-')[-1] or 'products'
    return jsonify(info)


@app.route('/categories', methods=['GET'])
def get_categories():
    """
    GET endpoint to retrieve all available categories.
    Returns list of { name, level } where level is 'primary', 'secondary', or 'tertiary'.
    When using DynamoDB, reads from the categories table; otherwise derives from products.
    """
    if USE_DYNAMODB and DYNAMODB_PRODUCTS_TABLE:
        rows = load_categories_from_dynamodb()
        level_map = {1: 'primary', 2: 'secondary', 3: 'tertiary'}
        categories_list = [
            {'name': r.get('path') or '', 'level': level_map.get(int(r.get('level', 0)), 'primary')}
            for r in rows
        ]
        categories_list.sort(key=lambda x: (['primary', 'secondary', 'tertiary'].index(x['level']), x['name']))
        return jsonify(categories_list)

    products = load_products()
    primary_categories = set()
    secondary_categories = set()
    tertiary_categories = set()
    for product in products:
        cat = product.get('category') or {}
        p = cat.get('primary') or product.get('primary_category')
        s = cat.get('secondary') or product.get('secondary_category')
        t = cat.get('tertiary') or product.get('tertiary_category')
        if p:
            primary_categories.add(p)
        if s:
            secondary_categories.add(s)
        if t:
            tertiary_categories.add(t)
    categories_dict = {}
    for cat in primary_categories:
        categories_dict[cat] = 'primary'
    for cat in secondary_categories:
        if cat not in categories_dict:
            categories_dict[cat] = 'secondary'
    for cat in tertiary_categories:
        if cat not in categories_dict:
            categories_dict[cat] = 'tertiary'
    categories_list = [{'name': name, 'level': level} for name, level in categories_dict.items()]
    level_order = {'primary': 0, 'secondary': 1, 'tertiary': 2}
    categories_list.sort(key=lambda x: (level_order[x['level']], x['name']))
    return jsonify(categories_list)


def _product_matches_category_filters(product, p_category=None, s_category=None, t_category=None):
    """
    True if the product matches the most specific category filter provided.
    Supports both category: { primary, secondary, tertiary } and flat primary_category etc.
    """
    cat = product.get('category') or {}
    t_val = cat.get('tertiary') or product.get('tertiary_category')
    s_val = cat.get('secondary') or product.get('secondary_category')
    p_val = cat.get('primary') or product.get('primary_category')
    if t_category:
        return t_val == t_category
    elif s_category:
        return s_val == s_category
    elif p_category:
        return p_val == p_category
    return True


@app.route('/products', methods=['GET'])
def get_products():
    """
    GET endpoint to retrieve products.
    Optional query params filter by category level; only the most specific category is used.

    Query parameters:
        p_category: primary_category (queries PrimaryCategory GSI)
        s_category: secondary_category (queries SecondaryCategory GSI)
        t_category: tertiary_category (queries TertiaryCategory GSI)

    Since categories are nested (tertiary -> secondary -> primary), the API uses only the most specific:
    - If t_category is provided, p_category and s_category are ignored
    - Else if s_category is provided, p_category is ignored
    - Else p_category is used
    """
    p_category = request.args.get('p_category', '').strip() or None
    s_category = request.args.get('s_category', '').strip() or None
    t_category = request.args.get('t_category', '').strip() or None
    # Only use the most specific filter
    if t_category:
        s_category = None
        p_category = None
    elif s_category:
        p_category = None
    has_filters = p_category or s_category or t_category

    if USE_DYNAMODB and DYNAMODB_PRODUCTS_TABLE and has_filters:
        products = get_products_by_category_filters_dynamodb(p_category, s_category, t_category)
        # DynamoDB filtered path returns raw paths; resolve image URLs once
        for product in products:
            if product.get('image_url'):
                product['image_url'] = get_image_url(product['image_url'])
    else:
        products = load_products()
        if has_filters:
            products = [
                p for p in products
                if _product_matches_category_filters(p, p_category, s_category, t_category)
            ]
        # load_products() already resolved image URLs; do not transform again

    return jsonify(products)


@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "customer-api"})


# Eagerly initialize boto3 clients and warm the product cache at import time.
# With gunicorn --preload this runs once in the master process before forking,
# so every worker starts ready to serve instantly.
if USE_DYNAMODB and DYNAMODB_PRODUCTS_TABLE:
    try:
        load_products()
        logger.info("Warm-up complete: DynamoDB client initialized, products cached")
    except Exception as e:
        logger.warning("Warm-up failed (will retry on first request): %s", e)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
