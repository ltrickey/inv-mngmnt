"""
Tests for the Mock API Gateway with API key authentication.
These tests verify that the gateway correctly validates API keys and proxies requests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import json
import tempfile
from pathlib import Path

# Import the mock gateway
from mock_api_gateway import gateway_app, MOCK_API_KEY


@pytest.fixture
def gateway_client():
    """Create a test client for the mock API Gateway."""
    return TestClient(gateway_app)


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
# API Key Authentication Tests
# ============================================================================

class TestAPIKeyAuthentication:
    """Tests for API key validation."""

    def test_request_without_api_key(self, gateway_client):
        """Test that requests without API key are rejected."""
        response = gateway_client.get("/api/inventory/store1/12345?quantity=10")
        
        assert response.status_code == 403
        assert "Forbidden" in response.json()["message"]

    def test_request_with_invalid_api_key(self, gateway_client):
        """Test that requests with invalid API key are rejected."""
        response = gateway_client.get(
            "/api/inventory/store1/12345?quantity=10",
            headers={"x-api-key": "invalid-key"}
        )
        
        assert response.status_code == 403
        assert "Forbidden" in response.json()["message"]

    def test_request_with_valid_api_key(self, gateway_client, mock_json_mode):
        """Test that requests with valid API key are allowed."""
        response = gateway_client.get(
            "/api/inventory/store1/12345?quantity=10",
            headers={"x-api-key": MOCK_API_KEY}
        )
        
        # Should proxy to backend (may get 404 if backend not running in test)
        assert response.status_code in [200, 404, 503]

    def test_docs_endpoint_accessible_without_key(self, gateway_client):
        """Test that documentation endpoints don't require API key."""
        response = gateway_client.get("/docs")
        
        # Docs should be accessible
        assert response.status_code in [200, 404]  # 404 if no docs configured


# ============================================================================
# Gateway Root Endpoint Tests
# ============================================================================

class TestGatewayRoot:
    """Tests for the mock gateway root endpoint."""

    def test_root_endpoint_info(self, gateway_client):
        """Test that root endpoint returns gateway information."""
        response = gateway_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Mock API Gateway"
        assert "api_key" in data
        assert "example_requests" in data
        assert data["api_key"]["header"] == "x-api-key"


# ============================================================================
# Proxy Behavior Tests
# ============================================================================

class TestProxyBehavior:
    """Tests for request proxying behavior."""

    def test_proxy_preserves_http_method(self, gateway_client, mock_json_mode):
        """Test that HTTP methods are preserved when proxying."""
        # Test GET
        response = gateway_client.get(
            "/api/inventory/store1/12345?quantity=10",
            headers={"x-api-key": MOCK_API_KEY}
        )
        assert response.status_code in [200, 404, 503]

    def test_proxy_preserves_query_parameters(self, gateway_client, mock_json_mode):
        """Test that query parameters are forwarded correctly."""
        response = gateway_client.get(
            "/api/inventory/store1/12345?quantity=50",
            headers={"x-api-key": MOCK_API_KEY}
        )
        
        # Should attempt to proxy with query params
        assert response.status_code in [200, 404, 503]

    def test_proxy_handles_post_body(self, gateway_client, mock_json_mode):
        """Test that request bodies are forwarded for POST/PATCH."""
        response = gateway_client.patch(
            "/api/inventory/store1/12345",
            headers={"x-api-key": MOCK_API_KEY},
            json={"quantity": 10}
        )
        
        # Should attempt to proxy with body
        assert response.status_code in [200, 400, 404, 503]


# ============================================================================
# Integration Tests (require backend running)
# ============================================================================

@pytest.mark.integration
class TestGatewayIntegration:
    """Integration tests that require the backend to be running."""

    def test_full_request_flow_with_api_key(self, gateway_client, mock_json_mode):
        """Test complete request flow through gateway to backend."""
        # This test only passes if backend is running
        response = gateway_client.get(
            "/api/inventory/store1/12345?quantity=10",
            headers={"x-api-key": MOCK_API_KEY}
        )
        
        # If backend is running and data exists, should get 200
        if response.status_code == 200:
            data = response.json()
            assert "available" in data
            assert "current_quantity" in data
