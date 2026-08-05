"""
Shared DynamoDB helpers for services that read the catalog tables
(products, stores, categories) and, for table naming, the inventory tables too.
"""

from decimal import Decimal

from boto3.dynamodb.types import TypeDeserializer

_deserializer = TypeDeserializer()


def derive_table_name(products_table: str, suffix: str) -> str:
    """
    Derive a related table name from the products table name.
    e.g. product-catalogue-test-products -> product-catalogue-test-stores
    """
    if not products_table or not products_table.endswith("-products"):
        return ""
    return products_table[: -len("-products")] + suffix


def deserialize_item(item: dict) -> dict:
    """Convert a raw DynamoDB item (AttributeValue map) into plain JSON-safe types."""
    raw = {k: _deserializer.deserialize(v) for k, v in item.items()}
    result = {}
    for k, v in raw.items():
        if isinstance(v, Decimal):
            result[k] = float(v)
        elif isinstance(v, list):
            result[k] = [float(x) if isinstance(x, Decimal) else x for x in v]
        else:
            result[k] = v
    return result
