import React, { useState } from 'react'
import { updateStockQuantity, deleteStockItem } from '../api'

export default function StockTable({ inventory, products, onRefresh }) {
  const [editingKey, setEditingKey] = useState(null)
  const [editQty, setEditQty] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const productMap = Object.fromEntries(
    (products || []).map((p) => [String(p.barcode), p])
  )

  const startEdit = (item) => {
    setEditingKey(`${item.store_id}:${item.barcode}`)
    setEditQty(item.quantity)
    setError('')
  }

  const cancelEdit = () => {
    setEditingKey(null)
    setError('')
  }

  const saveEdit = async (item) => {
    setBusy(true)
    setError('')
    try {
      await updateStockQuantity(item.store_id, item.barcode, editQty)
      setEditingKey(null)
      onRefresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (item) => {
    const product = productMap[String(item.barcode)]
    const name = product ? product.name : item.barcode
    if (!window.confirm(`Remove "${name}" from this store's inventory?`)) return

    setBusy(true)
    setError('')
    try {
      await deleteStockItem(item.store_id, item.barcode)
      onRefresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (!inventory || inventory.length === 0) {
    return <p className="empty-state">No products stocked at this store.</p>
  }

  return (
    <div className="stock-table-wrapper">
      {error && <p className="error">{error}</p>}
      <table className="stock-table">
        <thead>
          <tr>
            <th>Barcode</th>
            <th>Product Name</th>
            <th>Price</th>
            <th>% Off</th>
            <th>Quantity</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {inventory.map((item) => {
            const key = `${item.store_id}:${item.barcode}`
            const isEditing = editingKey === key
            const product = productMap[String(item.barcode)]
            return (
              <tr key={key}>
                <td>{item.barcode}</td>
                <td>{product ? product.name : '—'}</td>
                <td>${Number(item.price).toFixed(2)}</td>
                <td>{item.percent_off}%</td>
                <td>
                  {isEditing ? (
                    <input
                      type="number"
                      min="0"
                      value={editQty}
                      onChange={(e) => setEditQty(parseInt(e.target.value, 10) || 0)}
                      className="qty-input"
                    />
                  ) : (
                    item.quantity
                  )}
                </td>
                <td className="actions">
                  {isEditing ? (
                    <>
                      <button onClick={() => saveEdit(item)} disabled={busy} className="btn btn-save">
                        Save
                      </button>
                      <button onClick={cancelEdit} disabled={busy} className="btn btn-cancel">
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => startEdit(item)} disabled={busy} className="btn btn-edit">
                        Edit Qty
                      </button>
                      <button onClick={() => handleDelete(item)} disabled={busy} className="btn btn-danger">
                        Remove
                      </button>
                    </>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
