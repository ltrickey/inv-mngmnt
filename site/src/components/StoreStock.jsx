import React from 'react'

/**
 * Shows available stock for this product at the selected store.
 * Only renders when a store is selected.
 */
function StoreStock({ product, storeStock, storeName }) {
  if (!storeName || !storeStock) return null

  const item = storeStock.find((s) => String(s.barcode) === String(product.barcode))
  const quantity = item ? (item.quantity ?? 0) : null

  return (
    <div className="store-stock">
      <span className="store-stock-label">At {storeName}:</span>
      <span className="store-stock-value">
        {quantity === null
          ? '—'
          : quantity === 0
            ? 'Out of stock'
            : `${quantity} in stock`}
      </span>
    </div>
  )
}

export default StoreStock
