import React, { useState, useMemo } from 'react'
import { createStockItem } from '../api'

export default function AddProductModal({ products, inventory, storeId, onClose, onRefresh }) {
  const [selectedBarcode, setSelectedBarcode] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [price, setPrice] = useState('')
  const [percentOff, setPercentOff] = useState(0)
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
    if (!selectedBarcode || !selectedProduct || !price) return
    setBusy(true)
    setError('')
    try {
      await createStockItem(storeId, selectedBarcode, {
        quantity,
        price: parseFloat(price),
        percent_off: percentOff,
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

            <label htmlFor="price-input">Store Price:</label>
            <input
              id="price-input"
              type="number"
              min="0.01"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder={selectedProduct ? `Catalog: $${Number(selectedProduct.price).toFixed(2)}` : '0.00'}
              required
            />

            <label htmlFor="pct-off-input">% Off:</label>
            <input
              id="pct-off-input"
              type="number"
              min="0"
              max="100"
              value={percentOff}
              onChange={(e) => setPercentOff(parseInt(e.target.value, 10) || 0)}
            />

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
