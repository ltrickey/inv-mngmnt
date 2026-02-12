import React from 'react'

/**
 * Store dropdown: select a store to see stock and sales for that location.
 */
function StoreSelector({
  stores,
  selectedStoreId,
  onStoreChange,
  loading,
  error,
  salesError,
}) {
  return (
    <div className="filter-section store-selector">
      <h2>Select Store</h2>
      {loading && <p className="store-selector-loading">Loading stores…</p>}
      {error && <p className="store-selector-error" role="alert">{error}</p>}
      {salesError && (
        <p className="store-selector-sales-error" role="alert">
          Sales: {salesError}
        </p>
      )}
      {!loading && !error && (
        <div className="category-dropdown-group">
          <label htmlFor="store-select" className="category-dropdown-label">
            Store
          </label>
          <select
            id="store-select"
            className="category-select"
            value={selectedStoreId ?? ''}
            onChange={(e) => onStoreChange(e.target.value || null)}
          >
            <option value="">No store selected</option>
            {Array.isArray(stores) &&
              stores.map((store) => (
                <option key={store.store_id} value={store.store_id}>
                  {store.store_name || store.store_id}
                </option>
              ))}
          </select>
        </div>
      )}
    </div>
  )
}

export default StoreSelector
