from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal
from fastapi import HTTPException

import boto3
import json
from boto3.dynamodb.types import TypeDeserializer

from config import PRODUCTS_BY_STORE_TABLE, PRODUCTS_BY_STORE_FILE


# TODO: Move this to a separate file?
class InventoryItem(BaseModel):
    store_id: str
    barcode: str
    quantity: int
    percent_off: int
    price: float

# TODO: Move this to a separate file?
class InventoryDeductionItem(BaseModel):
    store_id: str
    barcode: str
    quantity: int

# Abstract DAO Interface to decouple data access from business logic
class InventoryDAO(ABC):
    @abstractmethod
    def get_all_by_store_id(self, store_id: str) -> List[InventoryItem]:
        pass

    @abstractmethod
    def get_by_store_id_and_barcode(self, store_id: str, barcode: str) -> InventoryItem:
        pass

    @abstractmethod
    def deduct_quantity(self, store_id: str, barcode: str, quantity: int) -> bool:
        pass

    # Deduct quantities of multiple products from a given store's inventory.  Return true if successfulf
    @abstractmethod
    def deduct_quantities(self, store_id: str, items: List[InventoryDeductionItem])-> bool:
        pass

    @abstractmethod
    def create_item(self, item: InventoryItem) -> InventoryItem:
        """Add a new product to a store's stock. Raises 409 if already exists."""
        pass

    @abstractmethod
    def update_item(self, store_id: str, barcode: str, quantity: int,
                    price: Optional[float] = None, percent_off: Optional[int] = None) -> InventoryItem:
        """Update an existing stock record. quantity is required; price and percent_off are optional."""
        pass

    @abstractmethod
    def delete_item(self, store_id: str, barcode: str) -> bool:
        """Remove a product from a store's stock. Raises 404 if not found."""
        pass


# Concrete DAO for accessing inventory Data from DynamoDB
class InventoryDAODynamoDB(InventoryDAO):
    def __init__(self, table_name: str, client: boto3.client):
        self.table_name = table_name
        self.client = client
        self.deserializer = TypeDeserializer()

    def _deserialize_item(self, item: dict) -> dict:
        """Deserialize a DynamoDB item to a Python dict."""
        raw = {k: self.deserializer.deserialize(v) for k, v in item.items()}
        result = {}
        for k, v in raw.items():
            if isinstance(v, Decimal):
                result[k] = float(v)
            elif isinstance(v, list):
                result[k] = [float(x) if isinstance(x, Decimal) else x for x in v]
            else:
                result[k] = v
        return result

    def get_all_by_store_id(self, store_id: str) -> List[InventoryItem]:
        # DynamoDB mode
        try:
            paginator = self.client.get_paginator("query")
            items: List[dict] = []
            for page in paginator.paginate(
                TableName=PRODUCTS_BY_STORE_TABLE,
                KeyConditionExpression="store_id = :sid",
                ExpressionAttributeValues={":sid": {"S": store_id}},
            ):
                for item in page.get("Items", []):
                    items.append(self._deserialize_item(item))
            return [InventoryItem(**item) for item in items]       
        except Exception as e:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail=f"DynamoDB query failed: {e}") from e

    def get_by_store_id_and_barcode(self, store_id: str, barcode: str) -> InventoryItem:
        try:
            
            resp = self.client.get_item(
                TableName=PRODUCTS_BY_STORE_TABLE,
                Key={"store_id": {"S": store_id}, "barcode": {"S": barcode}},
            )
            item = resp.get("Item")
            if not item:
                raise HTTPException(status_code=404, detail="Inventory item not found")
            return InventoryItem(**self._deserialize_item(item)) 
        except HTTPException:
            raise
        except Exception as e:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail=f"DynamoDB get_item failed: {e}") from e

    def deduct_quantity(self, store_id: str, barcode: str, quantity: int) -> bool:
        """
        Deduct a quantity from a product's inventory.
        Returns True if successful, raises HTTPException if insufficient quantity or item not found.
        """
        try:
            resp = self.client.update_item(
                TableName=PRODUCTS_BY_STORE_TABLE,
                Key={"store_id": {"S": store_id}, "barcode": {"S": barcode}},
                UpdateExpression="SET quantity = quantity - :qty",
                ConditionExpression="attribute_exists(store_id) AND attribute_exists(barcode) AND quantity >= :qty",
                ExpressionAttributeValues={
                    ":qty": {"N": str(quantity)}
                },
                ReturnValues="UPDATED_NEW"
            )
            return True
        except self.client.exceptions.ConditionalCheckFailedException:
            # Either item doesn't exist or insufficient quantity
            item = self.get_by_store_id_and_barcode(store_id, barcode)
            if item.quantity < quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient quantity. Available: {item.quantity}, Requested: {quantity}"
                )
            raise HTTPException(status_code=404, detail="Inventory item not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {e}") from e

    def deduct_quantities(self, store_id: str, items: List[InventoryItem]) -> bool:
        """
        Deduct quantities of multiple products from a store's inventory in a batch operation.
        Uses DynamoDB TransactWriteItems for atomicity.
        Returns True if successful, raises HTTPException if any item has insufficient quantity.
        """
        if not items:
            return True
        
        try:
            # Build transaction items
            transact_items = []
            for item in items:
                transact_items.append({
                    "Update": {
                        "TableName": PRODUCTS_BY_STORE_TABLE,
                        "Key": {
                            "store_id": {"S": store_id},
                            "barcode": {"S": item.barcode}
                        },
                        "UpdateExpression": "SET quantity = quantity - :qty",
                        "ConditionExpression": "attribute_exists(store_id) AND attribute_exists(barcode) AND quantity >= :qty",
                        "ExpressionAttributeValues": {
                            ":qty": {"N": str(item.quantity)}
                        }
                    }
                })
            
            # Execute transaction
            self.client.transact_write_items(TransactItems=transact_items)
            return True
        except self.client.exceptions.TransactionCanceledException as e:
            # Transaction failed - check which items caused the failure
            reasons = e.response.get("CancellationReasons", [])
            error_details = []
            for i, reason in enumerate(reasons):
                if reason.get("Code") == "ConditionalCheckFailed":
                    barcode = items[i].barcode if i < len(items) else "unknown"
                    error_details.append(f"Item {barcode}: insufficient quantity or not found")
            
            detail = "Transaction failed: " + "; ".join(error_details) if error_details else "One or more items have insufficient quantity"
            raise HTTPException(status_code=400, detail=detail)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DynamoDB transaction failed: {e}") from e

    def create_item(self, item: InventoryItem) -> InventoryItem:
        try:
            self.client.put_item(
                TableName=PRODUCTS_BY_STORE_TABLE,
                Item={
                    "store_id": {"S": item.store_id},
                    "barcode": {"S": item.barcode},
                    "quantity": {"N": str(item.quantity)},
                    "price": {"N": str(item.price)},
                    "percent_off": {"N": str(item.percent_off)},
                },
                ConditionExpression="attribute_not_exists(store_id) AND attribute_not_exists(barcode)",
            )
            return item
        except self.client.exceptions.ConditionalCheckFailedException:
            raise HTTPException(status_code=409, detail="Item already exists in store inventory")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DynamoDB put_item failed: {e}") from e

    def update_item(self, store_id: str, barcode: str, quantity: int,
                    price: Optional[float] = None, percent_off: Optional[int] = None) -> InventoryItem:
        try:
            set_parts = ["quantity = :qty"]
            expr_vals = {":qty": {"N": str(quantity)}}
            if price is not None:
                set_parts.append("price = :p")
                expr_vals[":p"] = {"N": str(price)}
            if percent_off is not None:
                set_parts.append("percent_off = :po")
                expr_vals[":po"] = {"N": str(percent_off)}

            resp = self.client.update_item(
                TableName=PRODUCTS_BY_STORE_TABLE,
                Key={"store_id": {"S": store_id}, "barcode": {"S": barcode}},
                UpdateExpression="SET " + ", ".join(set_parts),
                ConditionExpression="attribute_exists(store_id) AND attribute_exists(barcode)",
                ExpressionAttributeValues=expr_vals,
                ReturnValues="ALL_NEW",
            )
            return InventoryItem(**self._deserialize_item(resp["Attributes"]))
        except self.client.exceptions.ConditionalCheckFailedException:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DynamoDB update failed: {e}") from e

    def delete_item(self, store_id: str, barcode: str) -> bool:
        try:
            self.client.delete_item(
                TableName=PRODUCTS_BY_STORE_TABLE,
                Key={"store_id": {"S": store_id}, "barcode": {"S": barcode}},
                ConditionExpression="attribute_exists(store_id) AND attribute_exists(barcode)",
            )
            return True
        except self.client.exceptions.ConditionalCheckFailedException:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DynamoDB delete_item failed: {e}") from e


# Concrete DAO for accessing inventory Data from JSON file for local testing
class InventoryDAOJson(InventoryDAO):
    def __init__(self, file_path):
        self.file_path = file_path

    def get_all_by_store_id(self, store_id: str) -> List[InventoryItem]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        return [InventoryItem(**r) for r in rows if r.get("store_id") == store_id]


    def get_by_store_id_and_barcode(self, store_id: str, barcode: str) -> InventoryItem:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        for r in rows:
            if r.get("store_id") == store_id and r.get("barcode") == barcode:
                return InventoryItem(**r)
        raise HTTPException(status_code=404, detail="Inventory item not found")

    def deduct_quantity(self, store_id: str, barcode: str, quantity: int) -> bool:
        """
        Deduct a quantity from a product's inventory in the JSON file.
        Returns True if successful, raises HTTPException if insufficient quantity or item not found.
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        
        # Find and update the item
        item_found = False
        for r in rows:
            if r.get("store_id") == store_id and r.get("barcode") == barcode:
                item_found = True
                current_quantity = r.get("quantity", 0)
                
                if current_quantity < quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient quantity. Available: {current_quantity}, Requested: {quantity}"
                    )
                
                r["quantity"] = current_quantity - quantity
                break
        
        if not item_found:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        
        # Write back to file
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)
            return True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write to inventory file: {e}") from e

    def deduct_quantities(self, store_id: str, items: List[InventoryItem]) -> bool:
        """
        Deduct quantities of multiple products from a store's inventory.
        All operations are applied atomically (all succeed or all fail).
        Returns True if successful, raises HTTPException if any item has insufficient quantity.
        """
        if not items:
            return True
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []
        
        # First pass: validate all items exist and have sufficient quantity
        updates = []
        for item in items:
            found = False
            for i, r in enumerate(rows):
                if r.get("store_id") == store_id and r.get("barcode") == item.barcode:
                    found = True
                    current_quantity = r.get("quantity", 0)
                    
                    if current_quantity < item.quantity:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Insufficient quantity for item {item.barcode}. Available: {current_quantity}, Requested: {item.quantity}"
                        )
                    
                    updates.append((i, current_quantity - item.quantity))
                    break
            
            if not found:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Inventory item not found: store_id={store_id}, barcode={item.barcode}"
                )
        
        # Second pass: apply all updates
        for row_index, new_quantity in updates:
            rows[row_index]["quantity"] = new_quantity
        
        # Write back to file
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)
            return True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to write to inventory file: {e}") from e

    def create_item(self, item: InventoryItem) -> InventoryItem:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []

        for r in rows:
            if r.get("store_id") == item.store_id and r.get("barcode") == item.barcode:
                raise HTTPException(status_code=409, detail="Item already exists in store inventory")

        rows.append(item.model_dump())
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
        return item

    def update_item(self, store_id: str, barcode: str, quantity: int,
                    price: Optional[float] = None, percent_off: Optional[int] = None) -> InventoryItem:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []

        for r in rows:
            if r.get("store_id") == store_id and r.get("barcode") == barcode:
                r["quantity"] = quantity
                if price is not None:
                    r["price"] = price
                if percent_off is not None:
                    r["percent_off"] = percent_off
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, indent=2)
                return InventoryItem(**r)

        raise HTTPException(status_code=404, detail="Inventory item not found")

    def delete_item(self, store_id: str, barcode: str) -> bool:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            rows = []

        original_len = len(rows)
        rows = [r for r in rows if not (r.get("store_id") == store_id and r.get("barcode") == barcode)]

        if len(rows) == original_len:
            raise HTTPException(status_code=404, detail="Inventory item not found")

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
        return True
