# homework-series-ltrickey

## Flask Products REST API

A RESTful web service built with Python and Flask that provides product information.

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

### API Endpoints

#### GET /products

Returns a list of products. Supports optional category filtering.

**Query Parameters:**
- `category` (optional, can specify multiple): Filter products by category. Matches primary, secondary, or tertiary category. Products matching any of the specified categories will be returned.

**Examples:**

Get all products:
```bash
curl http://localhost:5000/products
```

Get products by single category:
```bash
curl http://localhost:5000/products?category=Dairy
curl http://localhost:5000/products?category=Fruits
curl http://localhost:5000/products?category=Organic
```

Get products by multiple categories:
```bash
curl http://localhost:5000/products?category=dairy&category=beverages
curl http://localhost:5000/products?category=Fruits&category=Vegetables
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

### Product Data

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
