import React from 'react'

/**
 * Product details component displaying barcode, categories, and ingredients.
 * Supports both nested (category.primary) and flat (primary_category) shapes.
 */
function ProductDetails({ product }) {
  const primary = product.category?.primary ?? product.primary_category
  const secondary = product.category?.secondary ?? product.secondary_category
  const tertiary = product.category?.tertiary ?? product.tertiary_category
  const ingredients = Array.isArray(product.ingredients) ? product.ingredients : []

  return (
    <div className="product-details">
      <div className="detail-row">
        <span className="detail-label">Barcode:</span>
        <span className="detail-value">{product.barcode} ({product.barcode_type})</span>
      </div>

      {primary && (
        <div className="detail-row">
          <span className="detail-label">Primary Category:</span>
          <span className="detail-value">{primary}</span>
        </div>
      )}

      {secondary && secondary !== 'NONE' && (
        <div className="detail-row">
          <span className="detail-label">Secondary Category:</span>
          <span className="detail-value">{secondary}</span>
        </div>
      )}

      {tertiary && tertiary !== 'NONE' && (
        <div className="detail-row">
          <span className="detail-label">Tertiary Category:</span>
          <span className="detail-value">{tertiary}</span>
        </div>
      )}

      {ingredients.length > 0 && (
        <div className="detail-row">
          <span className="detail-label">Ingredients:</span>
          <ul className="ingredients-list">
            {ingredients.map((ingredient, index) => (
              <li key={index}>{ingredient}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default ProductDetails
