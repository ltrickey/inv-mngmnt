from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Path to the products JSON file
PRODUCTS_FILE = 'products.json'


def load_products():
    """Load products from the JSON file."""
    try:
        with open(PRODUCTS_FILE, 'r') as f:
            return json.load(f)
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
    app.run(debug=True, host='0.0.0.0', port=8000)
