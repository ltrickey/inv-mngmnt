from flask import Flask, jsonify, request
import json
import os

app = Flask(__name__)

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
    app.run(debug=True, host='0.0.0.0', port=5000)
