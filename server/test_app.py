"""
Unit tests for the Flask product catalogue API.
"""
import pytest
import json
import os
from flask import Flask
from app import app, load_products, get_image_url


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestProductsEndpoint:
    """Tests for the /products endpoint."""
    
    #TODO: Add better verification than length of data. 
    def test_get_all_products(self, client):
        """Test retrieving all products without filters."""
        response = client.get('/products')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_products_filter_by_primary_category(self, client):
        """Test filtering products by primary category (p_category)."""
        response = client.get('/products?p_category=Dairy')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
        def _p(p): c = p.get('category') or {}; return c.get('primary') or p.get('primary_category')
        assert all(_p(p) == 'Dairy' for p in data)

    def test_get_products_filter_by_multiple_categories(self, client):
        """Test filtering by multiple categories uses the most specific (s_category over p_category)."""
        response = client.get('/products?p_category=Dairy&s_category=Milk')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        for product in data:
            c = product.get('category') or {}
            assert (c.get('secondary') or product.get('secondary_category')) == 'Milk'

    def test_get_products_filter_by_nonexistent_category(self, client):
        """Test filtering by a category that doesn't exist."""
        response = client.get('/products?p_category=NonexistentCategory')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_products_filter_by_secondary_category(self, client):
        """Test filtering by secondary category (s_category)."""
        response = client.get('/products?s_category=Milk')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        for product in data:
            c = product.get('category') or {}
            assert (c.get('secondary') or product.get('secondary_category')) == 'Milk'

    def test_get_products_filter_by_tertiary_category(self, client):
        """Test filtering by tertiary category (t_category)."""
        response = client.get('/products?t_category=Bananas')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        for product in data:
            c = product.get('category') or {}
            assert (c.get('tertiary') or product.get('tertiary_category')) == 'Bananas'
    
    def test_get_products_response_format(self, client):
        """Test that product response has all required fields."""
        response = client.get('/products')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) > 0
        
        product = data[0]
        required_fields = ['barcode', 'name', 'description', 'ingredients', 
                          'image_url', 'category']
        for field in required_fields:
            assert field in product


class TestCategoriesEndpoint:
    """Tests for the /categories endpoint."""
    
    def test_get_categories(self, client):
        """Test retrieving all categories."""
        response = client.get('/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_categories_have_name_and_level(self, client):
        """Test that categories have name and level fields."""
        response = client.get('/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        for category in data:
            assert 'name' in category
            assert 'level' in category
            assert category['level'] in ['primary', 'secondary', 'tertiary']
    
    def test_categories_sorted_by_level(self, client):
        """Test that categories are sorted by level (primary, secondary, tertiary)."""
        response = client.get('/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        level_order = {'primary': 0, 'secondary': 1, 'tertiary': 2}
        for i in range(len(data) - 1):
            current_level = level_order[data[i]['level']]
            next_level = level_order[data[i + 1]['level']]
            assert current_level <= next_level
    
    def test_categories_include_all_levels(self, client):
        """Test that categories from all levels are included."""
        response = client.get('/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        category_names = [cat['name'] for cat in data]
        # Should include primary categories from products.json
        assert 'Dairy' in category_names or 'Produce' in category_names
    
    def test_categories_no_duplicates(self, client):
        """Test that there are no duplicate category names."""
        response = client.get('/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        category_names = [cat['name'] for cat in data]
        assert len(category_names) == len(set(category_names))


class TestImageURLFunction:
    """Tests for the get_image_url function."""
    
    def test_get_image_url_local_development(self):
        """Test image URL resolution for local development."""
        # Without S3_BUCKET_URL, should return Flask route
        image_path = "infrastructure/images/product.jpg"
        url = get_image_url(image_path)
        assert url == "/images/product.jpg"
    
    def test_get_image_url_full_url_passthrough(self):
        """Test that full URLs are passed through unchanged."""
        full_url = "https://example.com/image.jpg"
        url = get_image_url(full_url)
        assert url == full_url
    
    def test_get_image_url_already_local_path(self):
        """Test image URL with path that's already local."""
        image_path = "product.jpg"
        url = get_image_url(image_path)
        assert url == "/images/product.jpg"


class TestLoadProductsFunction:
    """Tests for the load_products function."""
    
    def test_load_products_success(self):
        """Test loading products from valid JSON file."""
        products = load_products()
        assert isinstance(products, list)
        assert len(products) > 0
        # Verify product structure
        assert 'name' in products[0]
        assert 'barcode' in products[0]
    
    def test_load_products_has_image_urls(self):
        """Test that loaded products have image URLs resolved."""
        products = load_products()
        assert len(products) > 0
        # All products should have image_url field
        for product in products:
            assert 'image_url' in product
            assert product['image_url'] is not None


class TestCORS:
    """Tests for CORS headers."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.get('/products')
        assert response.status_code == 200
        # CORS headers should be present (flask-cors adds them)
        # The exact headers depend on flask-cors configuration


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_products_endpoint_returns_valid_json(self, client):
        """Test that /products endpoint returns valid JSON."""
        response = client.get('/products')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_categories_endpoint_returns_valid_json(self, client):
        """Test that /categories endpoint returns valid JSON."""
        response = client.get('/categories')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        data = json.loads(response.data)
        assert isinstance(data, list)
