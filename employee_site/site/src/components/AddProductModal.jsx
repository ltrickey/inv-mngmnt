import React, { useState, useMemo } from 'react'
import { createStockItem } from '../api'

export default function AddProductModal({ products, inventory, storeId, onClose, onRefresh }) {
  const [selectedBarcode, setSelectedBarcode] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const stockedBarcodes = useMemo(
    () => new Set((inventory || []).map((i) => String(i.barcode))),
    [inventory]
  )

  const available = useMemo(
    () => (products || []).filter((p) => !stockedBarcodes.has(String(p.barcode))),
    [products, stockedBarcodes]
  )

  const selectedProduct = available.find((p) => String(p.barcode) === selectedBarcode)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedBarcode || !selectedProduct) return
    setBusy(true)
    setError('')
    try {
      await createStockItem(storeId, selectedBarcode, {
        quantity,
        price: selectedProduct.price,
        percent_off: 0,
      })
      onRefresh()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Add Product to Store</h3>
        {available.length === 0 ? (
          <p>All catalog products are already stocked at this store.</p>
        ) : (
          <form onSubmit={handleSubmit}>
            <label htmlFor="product-select">Product:</label>
            <select
              id="product-select"
              value={selectedBarcode}
              onChange={(e) => setSelectedBarcode(e.target.value)}
              required
            >
              <option value="">-- Select a product --</option>
              {available.map((p) => (
                <option key={p.barcode} value={p.barcode}>
                  {p.name} ({p.barcode})
                </option>
              ))}
            </select>

            {selectedProduct && (
              <p className="product-price">Catalog price: ${Number(selectedProduct.price).toFixed(2)}</p>
            )}

            <label htmlFor="qty-input">Initial Quantity:</label>
            <input
              id="qty-input"
              type="number"
              min="0"
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value, 10) || 0)}
              required
            />

            {error && <p className="error">{error}</p>}

            <div className="modal-actions">
              <button type="submit" disabled={busy || !selectedBarcode} className="btn btn-save">
                {busy ? 'Adding...' : 'Add Product'}
              </button>
              <button type="button" onClick={onClose} disabled={busy} className="btn btn-cancel">
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
