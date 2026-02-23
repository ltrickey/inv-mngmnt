import React from 'react'

export default function StoreSelector({ stores, selectedStoreId, onChange, loading }) {
  if (loading) return <p>Loading stores...</p>

  return (
    <div className="store-selector">
      <label htmlFor="store-select">Store:</label>
      <select
        id="store-select"
        value={selectedStoreId || ''}
        onChange={(e) => onChange(e.target.value || null)}
      >
        <option value="">-- Select a store --</option>
        {stores.map((s) => (
          <option key={s.store_id} value={s.store_id}>
            {s.store_name || s.store_id}
          </option>
        ))}
      </select>
    </div>
  )
}
