from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import logging
import os
import time

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip .env loading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use DynamoDB for products when on EC2 (USE_DYNAMODB=1 and DYNAMODB_PRODUCTS_TABLE set); otherwise JSON files
USE_DYNAMODB = os.environ.get('USE_DYNAMODB', '').lower() in ('1', 'true', 'yes')
DYNAMODB_PRODUCTS_TABLE = os.environ.get('DYNAMODB_PRODUCTS_TABLE', '').strip()

# Determine if we're in production (serving React static files)
# In production, React build is in ../site-dist relative to server directory
REACT_BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'site-dist')
IS_PRODUCTION = os.path.exists(REACT_BUILD_DIR) and os.path.isdir(REACT_BUILD_DIR)

if IS_PRODUCTION:
    # Production: Serve React static files
    app = Flask(__name__, static_folder=REACT_BUILD_DIR, static_url_path='')
    CORS(app)  # Enable CORS for all routes
else:
    # Development: Don't serve static files (Vite dev server handles it)
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

# Register blueprints for stores, stock, sales.
# Stock and sales endpoints proxy to the FastAPI inventory service when INVENTORY_API_BASE_URL is set.
from stores import stores_bp
from stock import stock_bp
from sales import sales_bp
from data import load_categories_from_dynamodb
app.register_blueprint(stores_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(sales_bp)

# Serve static images from infrastructure/images directory
IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'infrastructure', 'images')
PLACEHOLDER_IMAGE = 'placeholder.png'

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from infrastructure/images directory; fallback to placeholder if missing."""
    path = os.path.join(IMAGES_DIR, filename)
    if not os.path.isfile(path):
        filename = PLACEHOLDER_IMAGE
    return send_from_directory(IMAGES_DIR, filename)

# Path to the products JSON file (used when running locally, not using DynamoDB)
# Seed data has been moved to the repo root: ../seed_data
PRODUCTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'seed_data', 'products.json')

# S3 configuration (optional - if not set, uses local images)
S3_BUCKET_URL = os.environ.get('S3_BUCKET_URL', None)


def get_image_url(image_path):
    """
    Get the full image URL based on environment configuration.
    If the image file does not exist on disk, returns the placeholder image URL
    so the API never points to a missing file (avoids 404s after re-seeds or renames).
    
    If S3_BUCKET_URL is set, prepends it to the image path for S3 storage.
    Otherwise, returns a Flask-served URL for local testing.
    
    Args:
        image_path: Relative path to the image (e.g., 'infrastructure/images/product.jpg')
    
    Returns:
        Full URL string for the image
    """
    if S3_BUCKET_URL:
        # TODO: IMPLEMENT PUlling images from S3Production: Use S3 bucket URL
        # Remove 'infrastructure/' prefix if present, S3 should have direct paths
        s3_path = image_path.replace('infrastructure/', '') if image_path.startswith('infrastructure/') else image_path
        return f"{S3_BUCKET_URL.rstrip('/')}/{s3_path}"
    else:
        # Local development: Use Flask static file serving
        if image_path.startswith(('http://', 'https://')):
            return image_path
        if image_path.startswith('/images/'):
            filename = image_path.replace('/images/', '')
        elif image_path.startswith('infrastructure/images/'):
            filename = image_path.replace('infrastructure/images/', '')
        elif image_path.startswith('infrastructure/'):
            filename = image_path.replace('infrastructure/', '')
        else:
            filename = image_path.lstrip('/')
        # If the file does not exist (e.g. old DynamoDB image_url, renamed file), use placeholder
        if filename and not os.path.isfile(os.path.join(IMAGES_DIR, filename)):
            filename = PLACEHOLDER_IMAGE
        return f"/images/{filename}"


def load_products_from_json():
    """Load products from the local seed_data JSON file."""
    try:
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


def _normalize_product_for_json(product):
    """Convert DynamoDB types (e.g. Decimal) to JSON-serializable types."""
    from decimal import Decimal
    result = {}
    for k, v in product.items():
        if isinstance(v, Decimal):
            result[k] = float(v)
        elif isinstance(v, list):
            result[k] = [float(x) if isinstance(x, Decimal) else x for x in v]
        else:
            result[k] = v
    return result


def _get_dynamodb_products_client():
    import boto3
    region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
    return boto3.client('dynamodb', region_name=region) if region else boto3.client('dynamodb')


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
    try:
        from boto3.dynamodb.types import TypeDeserializer
        client = _get_dynamodb_products_client()
        deserializer = TypeDeserializer()
        items = []

        if p_val:
            # Query GSI_Category by primary_category; optionally filter by category_path prefix
            key_condition = 'primary_category = :p'
            expr_vals = {':p': {'S': p_val}}
            filter_expr = None
            if t_val and s_val:
                filter_expr = 'begins_with(category_path, :prefix)'
                expr_vals[':prefix'] = {'S': s_val + '#' + t_val + '#'}
            elif s_val:
                filter_expr = 'begins_with(category_path, :prefix)'
                expr_vals[':prefix'] = {'S': s_val + '#'}
            elif t_val:
                # Tertiary only: category_path contains "#t_val#"
                filter_expr = 'contains(category_path, :ter)'
                expr_vals[':ter'] = {'S': '#' + t_val + '#'}

            paginator = client.get_paginator('query')
            paginate_kw = {
                'TableName': DYNAMODB_PRODUCTS_TABLE,
                'IndexName': 'GSI_Category',
                'KeyConditionExpression': key_condition,
                'ExpressionAttributeValues': expr_vals,
            }
            if filter_expr:
                paginate_kw['FilterExpression'] = filter_expr
            for page in paginator.paginate(**paginate_kw):
                for item in page.get('Items', []):
                    raw = {k: deserializer.deserialize(v) for k, v in item.items()}
                    items.append(_normalize_product_for_json(raw))
        else:
            # Secondary or tertiary only (no primary): scan with filter
            filter_parts = []
            expr_vals = {}
            if s_val:
                filter_parts.append('begins_with(category_path, :sec)')
                expr_vals[':sec'] = {'S': s_val + '#'}
            if t_val:
                filter_parts.append('contains(category_path, :ter)')
                expr_vals[':ter'] = {'S': '#' + t_val + '#'}
            if not expr_vals:
                return []
            paginator = client.get_paginator('scan')
            for page in paginator.paginate(
                TableName=DYNAMODB_PRODUCTS_TABLE,
                FilterExpression=' AND '.join(filter_parts),
                ExpressionAttributeValues=expr_vals,
            ):
                for item in page.get('Items', []):
                    raw = {k: deserializer.deserialize(v) for k, v in item.items()}
                    items.append(_normalize_product_for_json(raw))

        return items
    except Exception as e:
        logger.exception("DynamoDB get_products_by_category_filters failed: %s", e)
        return []


def load_products_from_dynamodb():
    """Load products from the DynamoDB products table (used when running on EC2)."""
    if not DYNAMODB_PRODUCTS_TABLE:
        return []
    try:
        from boto3.dynamodb.types import TypeDeserializer
        deserializer = TypeDeserializer()
        client = _get_dynamodb_products_client()
        paginator = client.get_paginator('scan')
        products = []
        for page in paginator.paginate(TableName=DYNAMODB_PRODUCTS_TABLE):
            for item in page.get('Items', []):
                raw = {k: deserializer.deserialize(v) for k, v in item.items()}
                products.append(_normalize_product_for_json(raw))
        return products
    except Exception as e:
        logger.exception("DynamoDB load_products failed: %s", e)
        return []


def load_products():
    """
    Load products from DynamoDB (on EC2) or from the JSON file (locally), then resolve image URLs.
    Image URLs are resolved based on S3_BUCKET_URL environment variable.
    If S3_BUCKET_URL is set, images are fetched from S3.
    Otherwise, images are served from local infrastructure/images directory.
    """
    if USE_DYNAMODB and DYNAMODB_PRODUCTS_TABLE:
        products = load_products_from_dynamodb()
    else:
        products = load_products_from_json()
    for product in products:
        if product.get('image_url'):
            product['image_url'] = get_image_url(product['image_url'])
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


# In production, serve React app for all non-API routes
# This must be defined AFTER all API routes to avoid intercepting them
if IS_PRODUCTION:
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        """Serve React app for all non-API routes."""
        # API routes are already handled above, so this only catches non-API routes
        # Serve index.html for all routes (React Router handles client-side routing)
        return send_from_directory(REACT_BUILD_DIR, 'index.html')
else:
    # Development: no React build; avoid 404 when someone hits Flask root or favicon
    @app.route('/')
    def dev_root():
        """In dev, frontend is served by Vite (e.g. port 3000). Use http:// (not https://)."""
        return (
            '<!DOCTYPE html><html><head><meta charset="utf-8"><title>API</title></head><body>'
            '<p>Backend API only. In development, open the <strong>frontend</strong> at '
            '<a href="http://localhost:3000">http://localhost:3000</a>.</p>'
            '<p>Use <strong>http://</strong> (not https://) when connecting to this server.</p>'
            '</body></html>'
        ), 200, {'Content-Type': 'text/html; charset=utf-8'}

    @app.route('/favicon.ico')
    def favicon():
        """Avoid 404 for browser favicon requests."""
        return '', 204


if __name__ == '__main__':
    # Development server only - NOT for production
    # For production, use a WSGI server like Gunicorn:
    #   gunicorn -w 4 -b 0.0.0.0:8000 app:app
    # host='0.0.0.0' makes the server accessible from other machines on the network
    # This is useful for testing from other devices during development
    app.run(debug=True, host='0.0.0.0', port=8000)
