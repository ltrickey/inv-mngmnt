"""
Data Manipulation layer for the Inventory API.
Provides factory function to get the appropriate DAO implementation.
"""
import os
import boto3

from config import USE_DYNAMODB, PRODUCTS_BY_STORE_TABLE, PRODUCTS_BY_STORE_FILE, SALES_EVENTS_TABLE
from inventory_dao import InventoryDAO, InventoryDAODynamoDB, InventoryDAOJson
from sales_dao import SalesEventDAO, SalesEventDAODynamoDB, SalesEventDAONoop


def _get_dynamodb_client():
    """Create and return a DynamoDB client."""
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    return boto3.client("dynamodb", region_name=region) if region else boto3.client("dynamodb")


DYNAMODB_CLIENT = _get_dynamodb_client()


def getMode():
    """Return the current mode (dynamodb or json)."""
    return "dynamodb" if USE_DYNAMODB else "json"


def get_sales_dao() -> SalesEventDAO:
    """Factory function to get the appropriate SalesEventDAO based on configuration."""
    if USE_DYNAMODB and SALES_EVENTS_TABLE and DYNAMODB_CLIENT:
        return SalesEventDAODynamoDB(SALES_EVENTS_TABLE, DYNAMODB_CLIENT)
    else:
        return SalesEventDAONoop()


def get_inventory_DAO() -> InventoryDAO:
    """
    Factory function to get the appropriate DAO implementation based on configuration.
    
    Returns:
        InventoryDAO: Either InventoryDAODynamoDB or InventoryDAOJson
    """
    if USE_DYNAMODB and PRODUCTS_BY_STORE_TABLE and DYNAMODB_CLIENT:
        return InventoryDAODynamoDB(PRODUCTS_BY_STORE_TABLE, DYNAMODB_CLIENT)
    else:
        return InventoryDAOJson(PRODUCTS_BY_STORE_FILE)