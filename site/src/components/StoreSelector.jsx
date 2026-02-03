import React from 'react'

/**
 * Store selector: dropdown of store names; when selected, shows store details in a box.
 */
function StoreSelector({ stores, selectedStoreId, onStoreChange, loading, error, salesError }) {
  const selectedStore = selectedStoreId
    ? stores.find((s) => s.store_id === selectedStoreId)
    : null

  return (
    <div className="store-selector-section filter-section">
      <h2>Select a store</h2>
      {error && <p className="store-selector-error">{error}</p>}
      {salesError && selectedStoreId && (
        <p className="store-selector-error store-selector-sales-error">{salesError}</p>
      )}
      <div className="store-selector-row">
        <div className="category-dropdown-group">
          <label htmlFor="store-select" className="category-dropdown-label">
            Store
          </label>
          <select
            id="store-select"
            className="category-select store-select"
            value={selectedStoreId || ''}
            onChange={(e) => onStoreChange(e.target.value || null)}
            disabled={loading}
          >
            <option value="">Choose a store…</option>
            {stores.map((store) => (
              <option key={store.store_id} value={store.store_id}>
                {store.store_name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {selectedStore && (
        <div className="store-info-box">
          <h3 className="store-info-title">{selectedStore.store_name}</h3>
          <dl className="store-info-dl">
            <dt>Address</dt>
            <dd>{selectedStore.store_address}</dd>
          </dl>
        </div>
      )}
    </div>
  )
}

export default StoreSelector
