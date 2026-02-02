from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import logging
import os

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
        if image_path.startswith('infrastructure/images/'):
            return image_path.replace('infrastructure/images/', '/images/')
        elif image_path.startswith('infrastructure/'):
            return image_path.replace('infrastructure/', '/')
        else:
            # If it's already a full URL (http/https), return as-is
            if image_path.startswith(('http://', 'https://')):
                return image_path
            # Otherwise, assume it's a local path and prepend /images/
            return f"/images/{image_path}"


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


def load_products_from_dynamodb():
    """Load products from the DynamoDB products table (used when running on EC2)."""
    if not DYNAMODB_PRODUCTS_TABLE:
        return []
    try:
        import boto3
        from boto3.dynamodb.types import TypeDeserializer
        deserializer = TypeDeserializer()
        region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
        client = boto3.client('dynamodb', region_name=region) if region else boto3.client('dynamodb')
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


@app.route('/products', methods=['GET'])
def get_products():
    """
    GET endpoint to retrieve products.
    Supports optional 'category' query parameters for filtering (can specify multiple).
    
    Query parameters:
        category (optional, can be multiple): Filter products by primary, secondary, or tertiary category.
                                            Products matching any of the specified categories will be returned.
                                            Example: ?category=dairy&category=beverages
    
    Returns:
        JSON response with list of products
    """
    products = load_products()
    
    # Get all category filters from query parameters (supports multiple)
    categories = request.args.getlist('category')
    
    if categories:
        # Filter products by categories (check primary, secondary, and tertiary)
        # A product matches if any of its categories match any of the requested categories
        filtered_products = [
            product for product in products
            if (product.get('primary_category') in categories or
                product.get('secondary_category') in categories or
                product.get('tertiary_category') in categories)
        ]
        return jsonify(filtered_products)
    
    # Return all products if no filter is specified
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


if __name__ == '__main__':
    # Development server only - NOT for production
    # For production, use a WSGI server like Gunicorn:
    #   gunicorn -w 4 -b 0.0.0.0:8000 app:app
    # host='0.0.0.0' makes the server accessible from other machines on the network
    # This is useful for testing from other devices during development
    app.run(debug=True, host='0.0.0.0', port=8000)
