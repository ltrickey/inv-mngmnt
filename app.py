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
    Supports optional 'category' query parameter for filtering.
    
    Query parameters:
        category (optional): Filter products by primary, secondary, or tertiary category
    
    Returns:
        JSON response with list of products
    """
    products = load_products()
    
    # Get category filter from query parameters
    category = request.args.get('category')
    
    if category:
        # Filter products by category (check primary, secondary, and tertiary)
        filtered_products = [
            product for product in products
            if (product.get('primary_category') == category or
                product.get('secondary_category') == category or
                product.get('tertiary_category') == category)
        ]
        return jsonify(filtered_products)
    
    # Return all products if no filter is specified
    return jsonify(products)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
