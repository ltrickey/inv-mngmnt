# Flask Products REST API

A RESTful web service built with Python and Flask that provides product information.

## Setup

1. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# On Windows: .venv\Scripts\activate
```

**Note:** If you encounter SSL errors during installation, make sure you're using a Python installation with SSL support. Try using the system Python:
```bash
# Remove existing .venv if it has SSL issues
rm -rf .venv

# Use system Python (usually has SSL support)
/usr/bin/python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Flask server:
```bash
python app.py
```

The server will start on `http://localhost:8000`

## API Endpoints

### GET /products

Returns a list of products. Supports optional category filtering.

**Query Parameters:**
- `category` (optional, can specify multiple): Filter products by category. Matches primary, secondary, or tertiary category. Products matching any of the specified categories will be returned.

**Examples:**

Get all products:
```bash
curl http://localhost:8000/products
```

Get products by single category:
```bash
curl http://localhost:8000/products?category=Dairy
curl http://localhost:8000/products?category=Fruits
curl http://localhost:8000/products?category=Organic
```

Get products by multiple categories:
```bash
curl http://localhost:8000/products?category=dairy&category=beverages
curl http://localhost:8000/products?category=Fruits&category=Vegetables
```

**Response Format:**
```json
[
  {
    "barcode": "0123456789012",
    "barcode_type": "GTIN",
    "name": "Organic Whole Milk",
    "description": "Fresh, organic whole milk from grass-fed cows",
    "ingredients": ["Organic whole milk"],
    "price": 4.99,
    "image_url": "https://example.com/images/milk.jpg",
    "primary_category": "Dairy",
    "secondary_category": "Beverages",
    "tertiary_category": null
  }
]
```

## Product Data

Products are stored in `products.json`. Each product includes:
- `barcode`: Barcode number (GTIN or PLU)
- `barcode_type`: Type of barcode ("GTIN" or "PLU")
- `name`: Product name
- `description`: Product description
- `ingredients`: List of ingredients
- `price`: Product price
- `image_url`: URL to product image
- `primary_category`: Primary product category
- `secondary_category`: Optional secondary category
- `tertiary_category`: Optional tertiary category

All products have a primary category, some have secondary, and those with tertiary also have secondary. Secondary categories are specific to their primary (e.g., "Fresh Vegetables" is only under "Produce", not mixed with "Frozen Vegetables").

### Primary Categories (general classifications):
Produce - for fresh fruits and vegetables
Dairy - for dairy products
Meat - for meat products
Seafood - for seafood
Beverages - for drinks
Dry Goods - for pantry items

### Secondary Categories (subcategories of primary):
Under Produce: Fresh Fruit, Fresh Vegetables
Under Dairy: Milk, Yogurt, Cheese, Butter, Eggs
Under Meat: Poultry, Beef
Under Seafood: Fish
Under Beverages: Juice
Under Dry Goods: Bread, Pasta, Oils, Cereal

### Tertiary Categories (specific types):
Examples: Bananas, Apples, Strawberries, Carrots, Spinach, Tomatoes, Broccoli, Onions, Chicken, Salmon, Whole Grain
