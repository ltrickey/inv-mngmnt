from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Serve static images from infrastructure/images directory for local development
@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve images from infrastructure/images directory for local testing."""
    return send_from_directory(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'infrastructure', 'images'), filename)

# Path to the products JSON file
PRODUCTS_FILE = 'products.json'

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
        # Production: Use S3 bucket URL
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


def load_products():
    """
    Load products from the JSON file and resolve image URLs.
    Image URLs are resolved based on S3_BUCKET_URL environment variable.
    If S3_BUCKET_URL is set, images are fetched from S3.
    Otherwise, images are served from local infrastructure/images directory.
    """
    try:
        with open(PRODUCTS_FILE, 'r') as f:
            products = json.load(f)
        
        # Transform image URLs based on environment (S3 or local)
        for product in products:
            if 'image_url' in product:
                product['image_url'] = get_image_url(product['image_url'])
        
        return products
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


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


if __name__ == '__main__':
    # Development server only - NOT for production
    # For production, use a WSGI server like Gunicorn:
    #   gunicorn -w 4 -b 0.0.0.0:8000 app:app
    # host='0.0.0.0' makes the server accessible from other machines on the network
    # This is useful for testing from other devices during development
    app.run(debug=True, host='0.0.0.0', port=8000)
