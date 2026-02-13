"""
Unit tests for the Inventory DAO classes.
Tests both InventoryDAOJson (file-based) and InventoryDAODynamoDB (AWS DynamoDB).
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from fastapi import HTTPException
import boto3
from moto import mock_aws

from dao import InventoryItem, InventoryDAOJson, InventoryDAODynamoDB


# ============================================================================
# Test Data Fixtures
# ============================================================================

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
def temp_json_file(sample_inventory_data):
    """Create a temporary JSON file with sample inventory data."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(sample_inventory_data, temp_file)
    temp_file.close()
    yield Path(temp_file.name)
    # Cleanup
    Path(temp_file.name).unlink()


@pytest.fixture
def empty_json_file():
    """Create an empty temporary JSON file."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump([], temp_file)
    temp_file.close()
    yield Path(temp_file.name)
    # Cleanup
    Path(temp_file.name).unlink()


# ============================================================================
# InventoryDAOJson Tests
# ============================================================================

class TestInventoryDAOJson:
    """Tests for the JSON file-based inventory DAO."""

    def test_get_all_by_store_id_success(self, temp_json_file):
        """Test retrieving all inventory items for a specific store."""
        dao = InventoryDAOJson(temp_json_file)
        items = dao.get_all_by_store_id("store1")
        
        assert len(items) == 2
        assert all(isinstance(item, InventoryItem) for item in items)
        assert all(item.store_id == "store1" for item in items)
        assert items[0].barcode == "12345"
        assert items[1].barcode == "67890"

    def test_get_all_by_store_id_no_results(self, temp_json_file):
        """Test retrieving inventory for a store with no items."""
        dao = InventoryDAOJson(temp_json_file)
        items = dao.get_all_by_store_id("store999")
        
        assert len(items) == 0
        assert isinstance(items, list)

    def test_get_all_by_store_id_missing_file(self):
        """Test handling of missing JSON file."""
        dao = InventoryDAOJson(Path("/nonexistent/file.json"))
        items = dao.get_all_by_store_id("store1")
        
        assert len(items) == 0

    def test_get_by_store_id_and_barcode_success(self, temp_json_file):
        """Test retrieving a specific inventory item."""
        dao = InventoryDAOJson(temp_json_file)
        item = dao.get_by_store_id_and_barcode("store1", "12345")
        
        assert isinstance(item, InventoryItem)
        assert item.store_id == "store1"
        assert item.barcode == "12345"
        assert item.quantity == 100
        assert item.price == 9.99

    def test_get_by_store_id_and_barcode_not_found(self, temp_json_file):
        """Test retrieving a non-existent inventory item."""
        dao = InventoryDAOJson(temp_json_file)
        
        with pytest.raises(HTTPException) as exc_info:
            dao.get_by_store_id_and_barcode("store999", "99999")
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    def test_deduct_quantity_success(self, temp_json_file):
        """Test successfully deducting quantity from inventory."""
        dao = InventoryDAOJson(temp_json_file)
        
        # Deduct 30 units from item with 100 units
        result = dao.deduct_quantity("store1", "12345", 30)
        assert result is True
        
        # Verify the quantity was updated
        item = dao.get_by_store_id_and_barcode("store1", "12345")
        assert item.quantity == 70

    def test_deduct_quantity_insufficient_stock(self, temp_json_file):
        """Test deducting more quantity than available."""
        dao = InventoryDAOJson(temp_json_file)
        
        # Try to deduct 150 units from item with 100 units
        with pytest.raises(HTTPException) as exc_info:
            dao.deduct_quantity("store1", "12345", 150)
        
        assert exc_info.value.status_code == 400
        assert "insufficient quantity" in exc_info.value.detail.lower()
        
        # Verify the quantity was not changed
        item = dao.get_by_store_id_and_barcode("store1", "12345")
        assert item.quantity == 100

    def test_deduct_quantity_exact_amount(self, temp_json_file):
        """Test deducting the exact quantity available."""
        dao = InventoryDAOJson(temp_json_file)
        
        result = dao.deduct_quantity("store1", "12345", 100)
        assert result is True
        
        # Verify the quantity is now 0
        item = dao.get_by_store_id_and_barcode("store1", "12345")
        assert item.quantity == 0

    def test_deduct_quantity_item_not_found(self, temp_json_file):
        """Test deducting quantity from non-existent item."""
        dao = InventoryDAOJson(temp_json_file)
        
        with pytest.raises(HTTPException) as exc_info:
            dao.deduct_quantity("store999", "99999", 10)
        
        assert exc_info.value.status_code == 404

    def test_deduct_quantities_success(self, temp_json_file):
        """Test successfully deducting multiple items in batch."""
        dao = InventoryDAOJson(temp_json_file)
        
        items_to_deduct = [
            InventoryItem(store_id="store1", barcode="12345", quantity=20, percent_off=0, price=9.99),
            InventoryItem(store_id="store1", barcode="67890", quantity=10, percent_off=0, price=19.99)
        ]
        
        result = dao.deduct_quantities("store1", items_to_deduct)
        assert result is True
        
        # Verify both quantities were updated
        item1 = dao.get_by_store_id_and_barcode("store1", "12345")
        assert item1.quantity == 80  # 100 - 20
        
        item2 = dao.get_by_store_id_and_barcode("store1", "67890")
        assert item2.quantity == 40  # 50 - 10

    def test_deduct_quantities_empty_list(self, temp_json_file):
        """Test deducting with empty list."""
        dao = InventoryDAOJson(temp_json_file)
        
        result = dao.deduct_quantities("store1", [])
        assert result is True

    def test_deduct_quantities_insufficient_stock(self, temp_json_file):
        """Test batch deduction with insufficient stock (should fail atomically)."""
        dao = InventoryDAOJson(temp_json_file)
        
        items_to_deduct = [
            InventoryItem(store_id="store1", barcode="12345", quantity=20, percent_off=0, price=9.99),
            InventoryItem(store_id="store1", barcode="67890", quantity=100, percent_off=0, price=19.99)  # Only 50 available
        ]
        
        with pytest.raises(HTTPException) as exc_info:
            dao.deduct_quantities("store1", items_to_deduct)
        
        assert exc_info.value.status_code == 400
        assert "67890" in exc_info.value.detail
        
        # Verify NO quantities were changed (atomic operation)
        item1 = dao.get_by_store_id_and_barcode("store1", "12345")
        assert item1.quantity == 100  # Unchanged
        
        item2 = dao.get_by_store_id_and_barcode("store1", "67890")
        assert item2.quantity == 50  # Unchanged

    def test_deduct_quantities_item_not_found(self, temp_json_file):
        """Test batch deduction with non-existent item."""
        dao = InventoryDAOJson(temp_json_file)
        
        items_to_deduct = [
            InventoryItem(store_id="store1", barcode="12345", quantity=20, percent_off=0, price=9.99),
            InventoryItem(store_id="store1", barcode="99999", quantity=10, percent_off=0, price=19.99)  # Doesn't exist
        ]
        
        with pytest.raises(HTTPException) as exc_info:
            dao.deduct_quantities("store1", items_to_deduct)
        
        assert exc_info.value.status_code == 404
        
        # Verify first item was not changed
        item1 = dao.get_by_store_id_and_barcode("store1", "12345")
        assert item1.quantity == 100


# ============================================================================
# InventoryDAODynamoDB Tests
# ============================================================================

@pytest.fixture
def mock_dynamodb_table():
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        # Create DynamoDB client
        client = boto3.client("dynamodb", region_name="us-east-1")
        
        # Create table
        table_name = "test-products-by-store"
        client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "store_id", "KeyType": "HASH"},
                {"AttributeName": "barcode", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "store_id", "AttributeType": "S"},
                {"AttributeName": "barcode", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        # Add test data
        client.put_item(
            TableName=table_name,
            Item={
                "store_id": {"S": "store1"},
                "barcode": {"S": "12345"},
                "quantity": {"N": "100"},
                "percent_off": {"N": "0"},
                "price": {"N": "9.99"}
            }
        )
        
        client.put_item(
            TableName=table_name,
            Item={
                "store_id": {"S": "store1"},
                "barcode": {"S": "67890"},
                "quantity": {"N": "50"},
                "percent_off": {"N": "10"},
                "price": {"N": "19.99"}
            }
        )
        
        client.put_item(
            TableName=table_name,
            Item={
                "store_id": {"S": "store2"},
                "barcode": {"S": "11111"},
                "quantity": {"N": "25"},
                "percent_off": {"N": "0"},
                "price": {"N": "5.99"}
            }
        )
        
        yield table_name, client


class TestInventoryDAODynamoDB:
    """Tests for the DynamoDB-based inventory DAO."""

    def test_get_all_by_store_id_success(self, mock_dynamodb_table):
        """Test retrieving all inventory items for a specific store from DynamoDB."""
        table_name, client = mock_dynamodb_table
        
        # Patch the imported variable
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            items = dao.get_all_by_store_id("store1")
        
        assert len(items) == 2
        assert all(isinstance(item, InventoryItem) for item in items)
        assert all(item.store_id == "store1" for item in items)

    def test_get_all_by_store_id_no_results(self, mock_dynamodb_table):
        """Test retrieving inventory for a store with no items."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            items = dao.get_all_by_store_id("store999")
        
        assert len(items) == 0

    def test_get_by_store_id_and_barcode_success(self, mock_dynamodb_table):
        """Test retrieving a specific inventory item from DynamoDB."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            item = dao.get_by_store_id_and_barcode("store1", "12345")
        
        assert isinstance(item, InventoryItem)
        assert item.store_id == "store1"
        assert item.barcode == "12345"
        assert item.quantity == 100
        assert item.price == 9.99

    def test_get_by_store_id_and_barcode_not_found(self, mock_dynamodb_table):
        """Test retrieving a non-existent inventory item from DynamoDB."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            
            with pytest.raises(HTTPException) as exc_info:
                dao.get_by_store_id_and_barcode("store999", "99999")
        
        assert exc_info.value.status_code == 404

    def test_deduct_quantity_success(self, mock_dynamodb_table):
        """Test successfully deducting quantity from DynamoDB inventory."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            
            result = dao.deduct_quantity("store1", "12345", 30)
            assert result is True
            
            # Verify the quantity was updated
            item = dao.get_by_store_id_and_barcode("store1", "12345")
            assert item.quantity == 70

    def test_deduct_quantity_insufficient_stock(self, mock_dynamodb_table):
        """Test deducting more quantity than available from DynamoDB."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            
            with pytest.raises(HTTPException) as exc_info:
                dao.deduct_quantity("store1", "12345", 150)
            
            assert exc_info.value.status_code == 400
            
            # Verify the quantity was not changed
            item = dao.get_by_store_id_and_barcode("store1", "12345")
            assert item.quantity == 100

    def test_deduct_quantity_item_not_found(self, mock_dynamodb_table):
        """Test deducting quantity from non-existent DynamoDB item."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            
            with pytest.raises(HTTPException) as exc_info:
                dao.deduct_quantity("store999", "99999", 10)
            
            assert exc_info.value.status_code in [404, 400]

    def test_deduct_quantities_success(self, mock_dynamodb_table):
        """Test successfully deducting multiple items in DynamoDB transaction."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            
            items_to_deduct = [
                InventoryItem(store_id="store1", barcode="12345", quantity=20, percent_off=0, price=9.99),
                InventoryItem(store_id="store1", barcode="67890", quantity=10, percent_off=0, price=19.99)
            ]
            
            result = dao.deduct_quantities("store1", items_to_deduct)
            assert result is True
            
            # Verify both quantities were updated
            item1 = dao.get_by_store_id_and_barcode("store1", "12345")
            assert item1.quantity == 80
            
            item2 = dao.get_by_store_id_and_barcode("store1", "67890")
            assert item2.quantity == 40

    def test_deduct_quantities_empty_list(self, mock_dynamodb_table):
        """Test deducting with empty list in DynamoDB."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            
            result = dao.deduct_quantities("store1", [])
            assert result is True

    def test_deduct_quantities_insufficient_stock(self, mock_dynamodb_table):
        """Test batch deduction with insufficient stock in DynamoDB (atomic failure)."""
        table_name, client = mock_dynamodb_table
        
        with patch('dao.PRODUCTS_BY_STORE_TABLE', table_name):
            dao = InventoryDAODynamoDB(table_name, client)
            
            items_to_deduct = [
                InventoryItem(store_id="store1", barcode="12345", quantity=20, percent_off=0, price=9.99),
                InventoryItem(store_id="store1", barcode="67890", quantity=100, percent_off=0, price=19.99)
            ]
            
            with pytest.raises(HTTPException) as exc_info:
                dao.deduct_quantities("store1", items_to_deduct)
            
            assert exc_info.value.status_code == 400
            
            # Verify NO quantities were changed (atomic operation)
            item1 = dao.get_by_store_id_and_barcode("store1", "12345")
            assert item1.quantity == 100
            
            item2 = dao.get_by_store_id_and_barcode("store1", "67890")
            assert item2.quantity == 50


# ============================================================================
# Integration Tests
# ============================================================================

class TestInventoryItemModel:
    """Tests for the InventoryItem Pydantic model."""

    def test_inventory_item_creation(self):
        """Test creating an InventoryItem instance."""
        item = InventoryItem(
            store_id="store1",
            barcode="12345",
            quantity=100,
            percent_off=10,
            price=9.99
        )
        
        assert item.store_id == "store1"
        assert item.barcode == "12345"
        assert item.quantity == 100
        assert item.percent_off == 10
        assert item.price == 9.99

    def test_inventory_item_validation(self):
        """Test InventoryItem validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            InventoryItem(
                store_id="store1",
                barcode="12345",
                quantity="not_a_number",  # Should be int
                percent_off=10,
                price=9.99
            )
