from abc import ABC, abstractmethod

from fastapi import HTTPException
from pydantic import BaseModel

from config import SALES_EVENTS_TABLE


class SaleEvent(BaseModel):
    store_id: str
    sale_id: str        # "YYYY-MM-DDTHH:mm:ss.ffffffZ#<transaction_id>#<barcode>" - time-sortable, unique per line item
    transaction_id: str # POS-supplied ID shared across all line items in one basket
    barcode: str
    quantity: int
    unit_price: float   # Final price per unit after discount at time of sale
    revenue: float      # unit_price * quantity


class SalesEventDAO(ABC):
    @abstractmethod
    def record_sale(self, event: SaleEvent) -> None:
        pass

    @abstractmethod
    def record_sales(self, events: list[SaleEvent]) -> None:
        pass


class SalesEventDAODynamoDB(SalesEventDAO):
    def __init__(self, table_name: str, client):
        self.table_name = table_name
        self.client = client

    def record_sale(self, event: SaleEvent) -> None:
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item={
                    "store_id":       {"S": event.store_id},
                    "sale_id":        {"S": event.sale_id},
                    "transaction_id": {"S": event.transaction_id},
                    "barcode":        {"S": event.barcode},
                    "quantity":       {"N": str(event.quantity)},
                    "unit_price":     {"N": str(event.unit_price)},
                    "revenue":        {"N": str(event.revenue)},
                },
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to record sale event: {e}") from e

    def record_sales(self, events: list[SaleEvent]) -> None:
        """Write multiple sale events in a single batch (up to 25 items per DynamoDB limit)."""
        if not events:
            return
        try:
            request_items = [
                {
                    "PutRequest": {
                        "Item": {
                            "store_id":       {"S": e.store_id},
                            "sale_id":        {"S": e.sale_id},
                            "transaction_id": {"S": e.transaction_id},
                            "barcode":        {"S": e.barcode},
                            "quantity":       {"N": str(e.quantity)},
                            "unit_price":     {"N": str(e.unit_price)},
                            "revenue":        {"N": str(e.revenue)},
                        }
                    }
                }
                for e in events
            ]
            self.client.batch_write_item(
                RequestItems={self.table_name: request_items}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to record sale events: {e}") from e


class SalesEventDAONoop(SalesEventDAO):
    """No-op implementation for local/JSON mode -- sale events are silently dropped."""

    def record_sale(self, event: SaleEvent) -> None:
        pass

    def record_sales(self, events: list[SaleEvent]) -> None:
        pass
