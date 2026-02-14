"""
Integration tests for the FastAPI inventory service endpoints.
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from dao import InventoryItem


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_inventory_data():
    """Sample inventory data for testing."""
    return [
        {
            "store_id": "store1",
            "barcode": "12345",
            "quantity": 100,
            "percent_off": 0,
            "price": 9.99
        },
        {
            "store_id": "store1",
            "barcode": "67890",
            "quantity": 50,
            "percent_off": 10,
            "price": 19.99
        },
        {
            "store_id": "store2",
            "barcode": "11111",
            "quantity": 25,
            "percent_off": 0,
            "price": 5.99
        }
    ]


@pytest.fixture
def mock_json_mode(sample_inventory_data):
    """Mock the inventory service to use JSON mode with test data."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(sample_inventory_data, temp_file)
    temp_file.close()
    
    with patch('inventory.USE_DYNAMODB', False), \
         patch('inventory.PRODUCTS_BY_STORE_FILE', Path(temp_file.name)):
        yield Path(temp_file.name)
    
    # Cleanup
    Path(temp_file.name).unlink()


# ============================================================================
# Health Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint returns OK."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "mode" in data

    def test_health_check_shows_json_mode(self, client, mock_json_mode):
        """Test health check shows JSON mode when configured."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "json"


# ============================================================================
# List Inventory Endpoint Tests
# ============================================================================

class TestListInventoryEndpoint:
    """Tests for GET /inventory/{store_id} endpoint."""

    def test_list_inventory_for_store_success(self, client, mock_json_mode):
        """Test retrieving all inventory for a store."""
        response = client.get("/inventory/store1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Verify all items belong to store1
        for item in data:
            assert item["store_id"] == "store1"
            assert "barcode" in item
            assert "quantity" in item
            assert "price" in item
            assert "percent_off" in item

    def test_list_inventory_for_store_empty(self, client, mock_json_mode):
        """Test retrieving inventory for a store with no items."""
        response = client.get("/inventory/store999")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_inventory_response_format(self, client, mock_json_mode):
        """Test that inventory response has all required fields."""
        response = client.get("/inventory/store1")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        
        item = data[0]
        required_fields = ['store_id', 'barcode', 'quantity', 'price', 'percent_off']
        for field in required_fields:
            assert field in item


# ============================================================================
# Get Inventory Item Endpoint Tests
# ============================================================================

class TestGetInventoryItemEndpoint:
    """Tests for GET /inventory/{store_id}/{barcode} endpoint."""

    def test_get_inventory_item_success(self, client, mock_json_mode):
        """Test retrieving a specific inventory item."""
        response = client.get("/inventory/store1/12345")
        
        assert response.status_code == 200
        data = response.json()
        assert data["store_id"] == "store1"
        assert data["barcode"] == "12345"
        assert data["quantity"] == 100
        assert data["price"] == 9.99
        assert data["percent_off"] == 0

    def test_get_inventory_item_not_found(self, client, mock_json_mode):
        """Test retrieving a non-existent inventory item."""
        response = client.get("/inventory/store999/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_inventory_item_wrong_store(self, client, mock_json_mode):
        """Test retrieving an item with wrong store_id."""
        response = client.get("/inventory/store2/12345")
        
        assert response.status_code == 404


# ============================================================================
# CORS and Headers Tests
# ============================================================================

class TestAPIHeaders:
    """Tests for API headers and response format."""

    def test_content_type_json(self, client, mock_json_mode):
        """Test that endpoints return JSON content type."""
        response = client.get("/inventory/store1")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_health_endpoint_content_type(self, client):
        """Test health endpoint returns JSON."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


# ============================================================================
# OpenAPI Documentation Tests
# ============================================================================

class TestOpenAPIDocumentation:
    """Tests for OpenAPI documentation endpoints."""

    def test_openapi_json_available(self, client):
        """Test that OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Inventory Service"

    def test_openapi_has_inventory_endpoints(self, client):
        """Test that OpenAPI schema includes inventory endpoints."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        paths = data["paths"]
        
        assert "/health" in paths
        assert "/inventory/{store_id}" in paths
        assert "/inventory/{store_id}/{barcode}" in paths


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in the API."""

    def test_invalid_store_id_format_handled(self, client, mock_json_mode):
        """Test that invalid store IDs are handled gracefully."""
        # FastAPI/Starlette should handle path parameters gracefully
        response = client.get("/inventory/store%20with%20spaces")
        
        # Should either return 200 with empty list or handle the space in store_id
        assert response.status_code in [200, 404, 422]

    def test_special_characters_in_barcode(self, client, mock_json_mode):
        """Test handling of special characters in barcode."""
        response = client.get("/inventory/store1/barcode-with-dashes")
        
        # Should return 404 if not found, not crash
        assert response.status_code == 404


# ============================================================================
# Integration Tests with DAO
# ============================================================================

class TestDAOIntegration:
    """Integration tests between endpoints and DAO layer."""

    def test_endpoint_uses_correct_dao(self, client, mock_json_mode):
        """Test that endpoints use the correct DAO based on configuration."""
        with patch('inventory.USE_DYNAMODB', False):
            response = client.get("/health")
            assert response.json()["mode"] == "json"
            
            # Verify we can retrieve data
            response = client.get("/inventory/store1")
            assert response.status_code == 200
            assert len(response.json()) > 0

    def test_multiple_requests_consistent(self, client, mock_json_mode):
        """Test that multiple requests return consistent data."""
        response1 = client.get("/inventory/store1/12345")
        response2 = client.get("/inventory/store1/12345")
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


# ============================================================================
# External API Endpoint Tests
# ============================================================================

class TestCheckStockEndpoint:
    """Tests for GET /api/inventory/{store_id}/{barcode}?quantity=N endpoint."""

    def test_check_stock_sufficient(self, client, mock_json_mode):
        """Test checking stock when sufficient quantity is available."""
        response = client.get("/api/inventory/store1/12345?quantity=50")
        
        assert response.status_code == 200
        data = response.json()
        assert data["store_id"] == "store1"
        assert data["barcode"] == "12345"
        assert data["available"] is True
        assert data["current_quantity"] == 100
        assert data["requested_quantity"] == 50

    def test_check_stock_insufficient(self, client, mock_json_mode):
        """Test checking stock when insufficient quantity is available."""
        response = client.get("/api/inventory/store1/12345?quantity=150")
        
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert data["current_quantity"] == 100
        assert data["requested_quantity"] == 150

    def test_check_stock_exact_amount(self, client, mock_json_mode):
        """Test checking stock when exact quantity is available."""
        response = client.get("/api/inventory/store1/12345?quantity=100")
        
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["current_quantity"] == 100
        assert data["requested_quantity"] == 100

    def test_check_stock_product_not_found(self, client, mock_json_mode):
        """Test checking stock for non-existent product."""
        response = client.get("/api/inventory/store1/99999?quantity=10")
        
        assert response.status_code == 404

    def test_check_stock_invalid_quantity(self, client, mock_json_mode):
        """Test checking stock with invalid quantity parameter."""
        response = client.get("/api/inventory/store1/12345?quantity=0")
        
        assert response.status_code == 422  # Validation error


class TestGetPriceEndpoint:
    """Tests for GET /api/inventory/{store_id}/{barcode}/price endpoint."""

    def test_get_price_no_discount(self, client, mock_json_mode):
        """Test getting price for product with no discount."""
        response = client.get("/api/inventory/store1/12345/price")
        
        assert response.status_code == 200
        data = response.json()
        assert data["store_id"] == "store1"
        assert data["barcode"] == "12345"
        assert data["original_price"] == 9.99
        assert data["percent_off"] == 0
        assert data["final_price"] == 9.99

    def test_get_price_with_discount(self, client, mock_json_mode):
        """Test getting price for product with discount."""
        response = client.get("/api/inventory/store1/67890/price")
        
        assert response.status_code == 200
        data = response.json()
        assert data["store_id"] == "store1"
        assert data["barcode"] == "67890"
        assert data["original_price"] == 19.99
        assert data["percent_off"] == 10
        # 10% off: 19.99 * 0.9 = 17.991 -> rounds to 17.99
        assert data["final_price"] == 17.99

    def test_get_price_product_not_found(self, client, mock_json_mode):
        """Test getting price for non-existent product."""
        response = client.get("/api/inventory/store1/99999/price")
        
        assert response.status_code == 404


class TestDeductQuantityEndpoint:
    """Tests for PATCH /api/inventory/{store_id}/{barcode} endpoint."""

    def test_deduct_quantity_success(self, client, mock_json_mode):
        """Test successfully deducting quantity."""
        response = client.patch(
            "/api/inventory/store1/12345",
            json={"quantity": 30}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["store_id"] == "store1"
        assert data["barcode"] == "12345"
        assert data["deducted_quantity"] == 30
        assert data["new_quantity"] == 70

    def test_deduct_quantity_insufficient_stock(self, client, mock_json_mode):
        """Test deducting more quantity than available."""
        response = client.patch(
            "/api/inventory/store1/12345",
            json={"quantity": 150}
        )
        
        assert response.status_code == 400
        assert "insufficient quantity" in response.json()["detail"].lower()

    def test_deduct_quantity_product_not_found(self, client, mock_json_mode):
        """Test deducting from non-existent product."""
        response = client.patch(
            "/api/inventory/store1/99999",
            json={"quantity": 10}
        )
        
        assert response.status_code == 404

    def test_deduct_quantity_invalid_quantity(self, client, mock_json_mode):
        """Test deducting with invalid quantity."""
        response = client.patch(
            "/api/inventory/store1/12345",
            json={"quantity": 0}
        )
        
        assert response.status_code == 422  # Validation error

    def test_deduct_quantity_negative_quantity(self, client, mock_json_mode):
        """Test deducting with negative quantity."""
        response = client.patch(
            "/api/inventory/store1/12345",
            json={"quantity": -10}
        )
        
        assert response.status_code == 422  # Validation error


class TestBatchDeductEndpoint:
    """Tests for PATCH /api/inventory/{store_id} endpoint (batch deduction)."""

    def test_batch_deduct_success(self, client, mock_json_mode):
        """Test successfully deducting multiple items."""
        response = client.patch(
            "/api/inventory/store1",
            json={
                "items": [
                    {"barcode": "12345", "quantity": 20},
                    {"barcode": "67890", "quantity": 10}
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["store_id"] == "store1"
        assert data["items_updated"] == 2
        assert len(data["items"]) == 2
        
        # Verify individual items
        item1 = next(i for i in data["items"] if i["barcode"] == "12345")
        assert item1["deducted_quantity"] == 20
        assert item1["new_quantity"] == 80
        
        item2 = next(i for i in data["items"] if i["barcode"] == "67890")
        assert item2["deducted_quantity"] == 10
        assert item2["new_quantity"] == 40

    def test_batch_deduct_insufficient_stock(self, client, mock_json_mode):
        """Test batch deduction with insufficient stock (should be atomic)."""
        response = client.patch(
            "/api/inventory/store1",
            json={
                "items": [
                    {"barcode": "12345", "quantity": 20},
                    {"barcode": "67890", "quantity": 100}  # Only 50 available
                ]
            }
        )
        
        assert response.status_code == 400
        
        # Verify first item was not deducted (atomic operation)
        check_response = client.get("/inventory/store1/12345")
        assert check_response.json()["quantity"] == 100  # Unchanged

    def test_batch_deduct_item_not_found(self, client, mock_json_mode):
        """Test batch deduction with non-existent item (should be atomic)."""
        response = client.patch(
            "/api/inventory/store1",
            json={
                "items": [
                    {"barcode": "12345", "quantity": 20},
                    {"barcode": "99999", "quantity": 10}  # Doesn't exist
                ]
            }
        )
        
        assert response.status_code == 404
        
        # Verify first item was not deducted (atomic operation)
        check_response = client.get("/inventory/store1/12345")
        assert check_response.json()["quantity"] == 100  # Unchanged

    def test_batch_deduct_empty_list(self, client, mock_json_mode):
        """Test batch deduction with empty items list."""
        response = client.patch(
            "/api/inventory/store1",
            json={"items": []}
        )
        
        assert response.status_code == 422  # Validation error

    def test_batch_deduct_invalid_quantity(self, client, mock_json_mode):
        """Test batch deduction with invalid quantity."""
        response = client.patch(
            "/api/inventory/store1",
            json={
                "items": [
                    {"barcode": "12345", "quantity": 0}
                ]
            }
        )
        
        assert response.status_code == 422  # Validation error
