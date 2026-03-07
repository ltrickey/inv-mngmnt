from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from inventory import get_inventory_DAO, get_sales_dao, getMode
from inventory_dao import InventoryDeductionItem, InventoryItem
from sales_dao import SaleEvent



app = FastAPI(
    title="Inventory Service",
    description="""
Manages per-store inventory and records point-of-sale transactions.

## Endpoint Groups

- **Health** — liveness check
- **Inventory (Internal)** — CRUD used by the employee site backend
- **Inventory (External)** — read-only + deduct endpoints for external vendors (fronted by API Gateway)
- **POS** — basket checkout: atomically deducts inventory and writes sale events for reporting

## Design Notes

Sales recording is co-located with inventory management so that inventory deduction and
sale event creation can be executed in a single atomic DynamoDB transaction. This is
intentional — the sales data is used for financial reporting and must be consistent with
the inventory state at the moment of sale.
    """,
    version="1.1.0",
    openapi_tags=[
        {"name": "Health"},
        {"name": "Inventory (Internal)", "description": "Used by the employee site BFF"},
        {"name": "Inventory (External)", "description": "Vendor-facing endpoints, fronted by API Gateway"},
        {"name": "POS", "description": "Point-of-sale checkout — atomic deduction + sale recording"},
    ],
)


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "mode": getMode(),
    }


@app.get("/inventory/{store_id}", tags=["Inventory (Internal)"])
def list_inventory_for_store(store_id: str) -> List[InventoryItem]:
    """
    Return all inventory rows for a given store_id.
    - When USE_DYNAMODB=1 and PRODUCTS_BY_STORE_TABLE is set, read from DynamoDB.
    - Otherwise, read from local seed_data/products_by_store.json.
    """
    return get_inventory_DAO().get_all_by_store_id(store_id)


@app.get("/inventory/{store_id}/{barcode}", tags=["Inventory (Internal)"])
def get_inventory_item(store_id: str, barcode: str) -> InventoryItem:
    """
    Return a single inventory row for (store_id, barcode) or 404 if not found.
    """
    return get_inventory_DAO().get_by_store_id_and_barcode(store_id, barcode)


# ============================================================================
# Internal CRUD Endpoints (called by employee site backend)
# ============================================================================

class CreateInventoryItemRequest(BaseModel):
    quantity: int = Field(..., ge=0)
    price: float = Field(..., gt=0)
    percent_off: int = Field(0, ge=0, le=100)


class UpdateInventoryItemRequest(BaseModel):
    quantity: int = Field(..., ge=0)
    price: Optional[float] = Field(None, gt=0)
    percent_off: Optional[int] = Field(None, ge=0, le=100)


@app.post("/inventory/{store_id}/{barcode}", response_model=InventoryItem, status_code=201, tags=["Inventory (Internal)"])
def create_inventory_item(store_id: str, barcode: str, request: CreateInventoryItemRequest):
    """Add a product to a store's inventory. Returns 409 if it already exists."""
    item = InventoryItem(
        store_id=store_id,
        barcode=barcode,
        quantity=request.quantity,
        price=request.price,
        percent_off=request.percent_off,
    )
    return get_inventory_DAO().create_item(item)


@app.put("/inventory/{store_id}/{barcode}", response_model=InventoryItem, tags=["Inventory (Internal)"])
def update_inventory_item(store_id: str, barcode: str, request: UpdateInventoryItemRequest):
    """Update an existing stock record. quantity is required; price and percent_off are optional."""
    return get_inventory_DAO().update_item(
        store_id, barcode,
        quantity=request.quantity,
        price=request.price,
        percent_off=request.percent_off,
    )


@app.delete("/inventory/{store_id}/{barcode}", status_code=204, tags=["Inventory (Internal)"])
def delete_inventory_item(store_id: str, barcode: str):
    """Remove a product from a store's inventory. Returns 404 if not found."""
    get_inventory_DAO().delete_item(store_id, barcode)


# ============================================================================
# Request/Response Models for External API
# ============================================================================

class StockCheckResponse(BaseModel):
    """Response model for stock availability check."""
    store_id: str
    barcode: str
    available: bool
    current_quantity: int
    requested_quantity: int


class PriceResponse(BaseModel):
    """Response model for price with sales applied."""
    store_id: str
    barcode: str
    original_price: float
    percent_off: int
    final_price: float


class DeductQuantityRequest(BaseModel):
    """Request model for deducting a single product quantity."""
    quantity: int = Field(..., gt=0, description="Quantity to deduct (must be positive)")


class DeductQuantityResponse(BaseModel):
    """Response model for single quantity deduction."""
    success: bool
    store_id: str
    barcode: str
    deducted_quantity: int
    new_quantity: int


class BatchDeductItem(BaseModel):
    """Item in batch deduct request."""
    barcode: str
    quantity: int = Field(..., gt=0, description="Quantity to deduct (must be positive)")


class BatchDeductRequest(BaseModel):
    """Request model for batch deduction."""
    items: List[BatchDeductItem] = Field(..., min_length=1, description="List of items to deduct")


class BatchDeductResponse(BaseModel):
    """Response model for batch deduction."""
    success: bool
    store_id: str
    items_updated: int
    items: List[dict]


# ============================================================================
# External API Endpoints
# ============================================================================

@app.get("/api/inventory/{store_id}/{barcode}", response_model=StockCheckResponse, tags=["Inventory (External)"])
def check_stock_availability(
    store_id: str,
    barcode: str,
    quantity: int = Query(..., gt=0, description="Minimum quantity to check for")
) -> StockCheckResponse:
    """
    Check if a given store has at least a certain amount of a product in stock.
    GET request on an inventory item with quantity filter.
    
    Args:
        store_id: The store ID
        barcode: The product barcode
        quantity: Minimum quantity required (query parameter)
        
    Returns:
        StockCheckResponse with availability status and current quantity
        
    Raises:
        404: If the product is not found in the store's inventory
        422: If quantity is invalid (must be > 0)
    """
    dao = get_inventory_DAO()
    item = dao.get_by_store_id_and_barcode(store_id, barcode)
    
    return StockCheckResponse(
        store_id=store_id,
        barcode=barcode,
        available=item.quantity >= quantity,
        current_quantity=item.quantity,
        requested_quantity=quantity
    )


@app.get("/api/inventory/{store_id}/{barcode}/price", response_model=PriceResponse, tags=["Inventory (External)"])
def get_product_price(store_id: str, barcode: str):
    """
    Get the price of a given product at a given store, applying any relevant sales.
    
    Args:
        store_id: The store ID
        barcode: The product barcode
        
    Returns:
        PriceResponse with original price, discount, and final price
        
    Raises:
        404: If the product is not found in the store's inventory
    """
    dao = get_inventory_DAO()
    item = dao.get_by_store_id_and_barcode(store_id, barcode)
    
    # Calculate final price after discount
    discount_multiplier = (100 - item.percent_off) / 100
    final_price = round(item.price * discount_multiplier, 2)
    
    return PriceResponse(
        store_id=store_id,
        barcode=barcode,
        original_price=item.price,
        percent_off=item.percent_off,
        final_price=final_price
    )


#Using patch as it is updating the quantity of an item in the inventory.
@app.patch("/api/inventory/{store_id}/{barcode}", response_model=DeductQuantityResponse, tags=["Inventory (External)"])
def deduct_product_quantity(
    store_id: str,
    barcode: str,
    request: DeductQuantityRequest,
) -> DeductQuantityResponse :
    """
    Deduct a quantity of a given product from a given store's inventory.
    
    Args:
        store_id: The store ID
        barcode: The product barcode
        request: DeductQuantityRequest with quantity to deduct
        
    Returns:
        DeductQuantityResponse with success status and new quantity
        
    Raises:
        400: If insufficient quantity available
        404: If the product is not found in the store's inventory
    """
    dao = get_inventory_DAO()
    
    # Get current quantity before deduction
    item_before = dao.get_by_store_id_and_barcode(store_id, barcode)
    
    # Deduct the quantity
    dao.deduct_quantity(store_id, barcode, request.quantity)
    
    # Get updated quantity after deduction
    item_after = dao.get_by_store_id_and_barcode(store_id, barcode)
    
    return DeductQuantityResponse(
        success=True,
        store_id=store_id,
        barcode=barcode,
        deducted_quantity=request.quantity,
        new_quantity=item_after.quantity
    )


@app.patch("/api/inventory/{store_id}", response_model=BatchDeductResponse, tags=["Inventory (External)"])
def deduct_product_quantities_batch(
    store_id: str,
    request: BatchDeductRequest
):
    """
    Deduct quantities of multiple products from a given store's inventory in one batch operation.
    This operation is atomic - either all items are deducted or none are.
    
    The fact that this is a "batch" operation is implicit in the request body containing multiple items.
    
    Args:
        store_id: The store ID
        request: BatchDeductRequest with list of items to deduct
        
    Returns:
        BatchDeductResponse with success status and updated items count
        
    Raises:
        400: If any item has insufficient quantity (none will be deducted)
        404: If any product is not found (none will be deducted)
    """
    dao = get_inventory_DAO()
    
    # Convert BatchDeductItems to InventoryItems for DAO
    items_to_deduct = [
        InventoryDeductionItem(
            store_id=store_id,
            barcode=item.barcode,
            quantity=item.quantity,
        )
        for item in request.items
    ]
    
    # Perform batch deduction (atomic operation)
    dao.deduct_quantities(store_id, items_to_deduct)
    
    # Build response with updated items
    updated_items = []
    for item in request.items:
        updated = dao.get_by_store_id_and_barcode(store_id, item.barcode)
        updated_items.append({
            "barcode": item.barcode,
            "deducted_quantity": item.quantity,
            "new_quantity": updated.quantity
        })
    
    return BatchDeductResponse(
        success=True,
        store_id=store_id,
        items_updated=len(updated_items),
        items=updated_items
    )


# ============================================================================
# POS (Point of Sale) Endpoints
# ============================================================================

class POSSaleItem(BaseModel):
    """One line item in a POS sale basket."""
    barcode: str
    quantity: int = Field(..., gt=0, description="Quantity sold (must be positive)")


class POSSaleRequest(BaseModel):
    """A full basket submitted by a POS terminal at checkout."""
    transaction_id: str = Field(..., description="Unique transaction ID from the POS terminal")
    items: List[POSSaleItem] = Field(..., min_length=1, description="Line items in the basket")


class POSSaleLineResult(BaseModel):
    barcode: str
    quantity: int
    unit_price: float
    revenue: float
    new_inventory_quantity: int


class POSSaleResponse(BaseModel):
    success: bool
    store_id: str
    transaction_id: str
    items: List[POSSaleLineResult]
    total_revenue: float


@app.post("/api/pos/sale/{store_id}", response_model=POSSaleResponse, status_code=201, tags=["POS"])
def record_pos_sale(store_id: str, request: POSSaleRequest):
    """
    Record a full POS basket sale for a store.

    This endpoint:
    1. Looks up the current price for each item in the basket
    2. Atomically deducts all inventory quantities (all-or-nothing)
    3. Persists a SaleEvent per line item (keyed by transaction_id) for report generation

    Args:
        store_id: The store submitting the sale
        request: POSSaleRequest with a POS-supplied transaction_id and list of line items

    Returns:
        POSSaleResponse with per-item unit prices, revenues, and updated inventory quantities

    Raises:
        400: If any item has insufficient inventory (nothing is deducted)
        404: If any barcode is not found in this store's inventory (nothing is deducted)
        409: If transaction_id has already been recorded (idempotency guard)
    """
    dao = get_inventory_DAO()
    sales_dao = get_sales_dao()

    # Capture a single timestamp for the whole transaction so all line items share it
    sale_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # 1. Fetch current price/percent_off for each item (before deduction)
    #    This also serves as an early 404 check — raises HTTPException if any barcode is missing.
    inventory_items = {
        item.barcode: dao.get_by_store_id_and_barcode(store_id, item.barcode)
        for item in request.items
    }

    # 2. Atomically deduct all inventory quantities
    items_to_deduct = [
        InventoryDeductionItem(store_id=store_id, barcode=item.barcode, quantity=item.quantity)
        for item in request.items
    ]
    dao.deduct_quantities(store_id, items_to_deduct)

    # 3. Build sale events and response items
    sale_events = []
    result_items = []
    for item in request.items:
        inv = inventory_items[item.barcode]
        unit_price = round(inv.price * (100 - inv.percent_off) / 100, 2)
        revenue = round(unit_price * item.quantity, 2)

        sale_events.append(SaleEvent(
            store_id=store_id,
            sale_id=f"{sale_timestamp}#{request.transaction_id}#{item.barcode}",
            transaction_id=request.transaction_id,
            barcode=item.barcode,
            quantity=item.quantity,
            unit_price=unit_price,
            revenue=revenue,
        ))

        updated = dao.get_by_store_id_and_barcode(store_id, item.barcode)
        result_items.append(POSSaleLineResult(
            barcode=item.barcode,
            quantity=item.quantity,
            unit_price=unit_price,
            revenue=revenue,
            new_inventory_quantity=updated.quantity,
        ))

    # 4. Persist all sale events in one batch write
    sales_dao.record_sales(sale_events)

    return POSSaleResponse(
        success=True,
        store_id=store_id,
        transaction_id=request.transaction_id,
        items=result_items,
        total_revenue=round(sum(i.revenue for i in result_items), 2),
    )
