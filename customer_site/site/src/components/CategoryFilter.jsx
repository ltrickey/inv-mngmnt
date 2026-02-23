import React from 'react'

/**
 * Cascading category dropdowns: primary (always), secondary (when primary selected), tertiary (when secondary selected).
 * Only one option per level can be selected.
 */
function CategoryFilter({
  primaryOptions,
  secondaryOptions,
  tertiaryOptions,
  selectedPrimary,
  selectedSecondary,
  selectedTertiary,
  onPrimaryChange,
  onSecondaryChange,
  onTertiaryChange,
}) {
  return (
    <div className="filter-section">
      <h2>Filter by Category</h2>
      <div className="category-dropdowns">
        <div className="category-dropdown-group">
          <label htmlFor="primary-category" className="category-dropdown-label">
            Primary category
          </label>
          <select
            id="primary-category"
            className="category-select"
            value={selectedPrimary}
            onChange={(e) => onPrimaryChange(e.target.value)}
          >
            <option value="">All</option>
            {primaryOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>

        {selectedPrimary && (
          <div className="category-dropdown-group">
            <label htmlFor="secondary-category" className="category-dropdown-label">
              Secondary category
            </label>
            <select
              id="secondary-category"
              className="category-select"
              value={selectedSecondary}
              onChange={(e) => onSecondaryChange(e.target.value)}
            >
              <option value="">All</option>
              {secondaryOptions.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        )}

        {selectedPrimary && selectedSecondary && tertiaryOptions.length > 0 && (
          <div className="category-dropdown-group">
            <label htmlFor="tertiary-category" className="category-dropdown-label">
              Tertiary category
            </label>
            <select
              id="tertiary-category"
              className="category-select"
              value={selectedTertiary}
              onChange={(e) => onTertiaryChange(e.target.value)}
            >
              <option value="">All</option>
              {tertiaryOptions.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </div>
  )
}

export default CategoryFilter
