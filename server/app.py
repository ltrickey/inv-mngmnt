from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import logging
import os
import time

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

# Register blueprints for stores, stock, sales (products/categories stay here)
from stores import stores_bp
from stock import stock_bp
from sales import sales_bp
app.register_blueprint(stores_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(sales_bp)

# Serve static images from infrastructure/images directory
@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from infrastructure/images directory."""
    images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'infrastructure', 'images')
    return send_from_directory(images_dir, filename)

# Path to the products JSON file (used when running locally, not using DynamoDB)
PRODUCTS_FILE = os.path.join(os.path.dirname(__file__), 'seed_data', 'products.json')

# S3 configuration (optional - if not set, uses local images)
S3_BUCKET_URL = os.environ.get('S3_BUCKET_URL', None)


def get_image_url(image_path):
    """
    Get the full image URL based on environment configuration.
    
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
        # Convert 'infrastructure/images/...' to '/images/...'
        if image_path.startswith(('http://', 'https://')):
            return image_path
        if image_path.startswith('/images/'):
            return image_path  # Already correct; avoid double /images/
        if image_path.startswith('infrastructure/images/'):
            return image_path.replace('infrastructure/images/', '/images/')
        if image_path.startswith('infrastructure/'):
            return image_path.replace('infrastructure/', '/')
        # Bare filename or relative path
        return f"/images/{image_path.lstrip('/')}"


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


def _barcodes_from_gsi_query(client, table_name, index_name, key_attr, category_value):
    """Query a category GSI and return set of barcodes. category_value must be non-empty (items with null are not in the index)."""
    barcodes = set()
    try:
        paginator = client.get_paginator('query')
        for page in paginator.paginate(
            TableName=table_name,
            IndexName=index_name,
            KeyConditionExpression=f'{key_attr} = :cat',
            ExpressionAttributeValues={':cat': {'S': category_value}},
        ):
            for item in page.get('Items', []):
                barcode = item.get('barcode', {}).get('S')
                if barcode:
                    barcodes.add(barcode)
    except Exception as e:
        logger.warning("DynamoDB GSI query %s failed for %s: %s", index_name, category_value, e)
    return barcodes


def get_products_by_category_filters_dynamodb(p_category=None, s_category=None, t_category=None):
    """
    Get products that match the given primary/secondary/tertiary category filters using DynamoDB GSIs.
    Each filter queries its corresponding GSI (PrimaryCategory, SecondaryCategory, TertiaryCategory).
    When multiple filters are set, barcode sets are intersected (product must match ALL).
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
        #TODO: I don't love this approach, see if we can change data model so we're not joining on client level, but OK for now.
        barcode_sets = []
        if p_val:
            barcode_sets.append(_barcodes_from_gsi_query(client, DYNAMODB_PRODUCTS_TABLE, 'PrimaryCategory', 'primary_category', p_val))
        if s_val:
            barcode_sets.append(_barcodes_from_gsi_query(client, DYNAMODB_PRODUCTS_TABLE, 'SecondaryCategory', 'secondary_category', s_val))
        if t_val:
            barcode_sets.append(_barcodes_from_gsi_query(client, DYNAMODB_PRODUCTS_TABLE, 'TertiaryCategory', 'tertiary_category', t_val))
        if not barcode_sets:
            return []
        result_barcodes = barcode_sets[0]
        for s in barcode_sets[1:]:
            result_barcodes = result_barcodes & s
        if not result_barcodes:
            return []
        barcode_list = list(result_barcodes)
        products = []
        for i in range(0, len(barcode_list), 100):
            chunk = barcode_list[i : i + 100]
            request_items = {
                DYNAMODB_PRODUCTS_TABLE: {
                    'Keys': [{'barcode': {'S': b}} for b in chunk],
                }
            }
            max_retries = 5
            retry_delay = 0.5  # seconds, then exponential backoff
            for attempt in range(max_retries + 1):
                resp = client.batch_get_item(RequestItems=request_items)
                for item in resp.get('Responses', {}).get(DYNAMODB_PRODUCTS_TABLE, []):
                    raw = {k: deserializer.deserialize(v) for k, v in item.items()}
                    products.append(_normalize_product_for_json(raw))
                request_items = resp.get('UnprocessedKeys') or {}
                if not request_items:
                    break
                if attempt < max_retries:
                    logger.warning(
                        "DynamoDB batch_get_item returned %s unprocessed keys (attempt %s/%s), retrying after %.2fs",
                        sum(len(v.get('Keys', [])) for v in request_items.values()),
                        attempt + 1,
                        max_retries,
                        retry_delay,
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 10.0)
                else:
                    logger.error(
                        "DynamoDB batch_get_item still had unprocessed keys after %s retries; some items omitted from results",
                        max_retries,
                    )
        return products
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
    Returns unique categories with their level (primary, secondary, tertiary).
    """
    products = load_products()
    primary_categories = set()
    secondary_categories = set()
    tertiary_categories = set()
    
    for product in products:
        if product.get('primary_category'):
            primary_categories.add(product.get('primary_category'))
        if product.get('secondary_category'):
            secondary_categories.add(product.get('secondary_category'))
        if product.get('tertiary_category'):
            tertiary_categories.add(product.get('tertiary_category'))
    
    # Build categories list with levels
    # TODO: Update this logic as we use data stores.
    # If a category appears at multiple levels, use the highest level (primary > secondary > tertiary)
    categories_dict = {}
    
    # First add primary categories
    for cat in primary_categories:
        categories_dict[cat] = 'primary'
    
    # Add secondary categories that aren't primary
    for cat in secondary_categories:
        if cat not in categories_dict:
            categories_dict[cat] = 'secondary'
    
    # Add tertiary categories that aren't primary or secondary
    for cat in tertiary_categories:
        if cat not in categories_dict:
            categories_dict[cat] = 'tertiary'
    
    # Convert to list of objects with name and level
    categories_list = [{'name': name, 'level': level} for name, level in categories_dict.items()]
    
    # Sort by level (primary first, then secondary, then tertiary), then by name
    level_order = {'primary': 0, 'secondary': 1, 'tertiary': 2}
    categories_list.sort(key=lambda x: (level_order[x['level']], x['name']))
    
    return jsonify(categories_list)


def _product_matches_category_filters(product, p_category=None, s_category=None, t_category=None):
    """True if the product matches all of the given primary/secondary/tertiary filters."""
    if p_category and product.get('primary_category') != p_category:
        return False
    if s_category and product.get('secondary_category') != s_category:
        return False
    if t_category and product.get('tertiary_category') != t_category:
        return False
    return True


@app.route('/products', methods=['GET'])
def get_products():
    """
    GET endpoint to retrieve products.
    Optional query params filter by category level; each uses its GSI when using DynamoDB.

    Query parameters:
        p_category: primary_category (queries PrimaryCategory GSI)
        s_category: secondary_category (queries SecondaryCategory GSI)
        t_category: tertiary_category (queries TertiaryCategory GSI)

    When multiple are provided, only products matching ALL filters are returned.
    Example: ?p_category=Dairy&s_category=Milk returns products with primary_category=Dairy and secondary_category=Milk.
    """
    p_category = request.args.get('p_category', '').strip() or None
    s_category = request.args.get('s_category', '').strip() or None
    t_category = request.args.get('t_category', '').strip() or None
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
