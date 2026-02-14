from typing import List

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from inventory import get_inventory_DAO, getMode
from dao import InventoryDeductionItem, InventoryItem



app = FastAPI(
    title="Inventory Service",
    description="""
    Inventory API backed by DynamoDB products_by_store table.
    
    ## External API Endpoints
    
    This service provides externally-facing API endpoints for:
    - Checking stock availability
    - Getting product prices with sales applied
    - Deducting inventory quantities (single and batch)
    
    All external endpoints are prefixed with `/api/inventory/`.
    """,
    version="1.0.0",
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": getMode(),
    }


@app.get("/inventory/{store_id}")
def list_inventory_for_store(store_id: str) -> List[InventoryItem]:
    """
    Return all inventory rows for a given store_id.
    - When USE_DYNAMODB=1 and PRODUCTS_BY_STORE_TABLE is set, read from DynamoDB.
    - Otherwise, read from local seed_data/products_by_store.json.
    """
    return get_inventory_DAO().get_all_by_store_id(store_id)


@app.get("/inventory/{store_id}/{barcode}")
def get_inventory_item(store_id: str, barcode: str) -> InventoryItem:
    """
    Return a single inventory row for (store_id, barcode) or 404 if not found.
    """
    return get_inventory_DAO().get_by_store_id_and_barcode(store_id, barcode)


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

@app.get("/api/inventory/{store_id}/{barcode}", response_model=StockCheckResponse)
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


@app.get("/api/inventory/{store_id}/{barcode}/price", response_model=PriceResponse)
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
@app.patch("/api/inventory/{store_id}/{barcode}", response_model=DeductQuantityResponse)
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


@app.patch("/api/inventory/{store_id}", response_model=BatchDeductResponse)
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
