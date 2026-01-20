import React from 'react'

/**
 * Product details component displaying barcode, categories, and ingredients
 */
function ProductDetails({ product }) {
  return (
    <div className="product-details">
      <div className="detail-row">
        <span className="detail-label">Barcode:</span>
        <span className="detail-value">{product.barcode} ({product.barcode_type})</span>
      </div>
      
      <div className="detail-row">
        <span className="detail-label">Primary Category:</span>
        <span className="detail-value">{product.primary_category}</span>
      </div>
      
      {product.secondary_category && (
        <div className="detail-row">
          <span className="detail-label">Secondary Category:</span>
          <span className="detail-value">{product.secondary_category}</span>
        </div>
      )}
      
      {product.tertiary_category && (
        <div className="detail-row">
          <span className="detail-label">Tertiary Category:</span>
          <span className="detail-value">{product.tertiary_category}</span>
        </div>
      )}
      
      <div className="detail-row">
        <span className="detail-label">Ingredients:</span>
        <ul className="ingredients-list">
          {product.ingredients.map((ingredient, index) => (
            <li key={index}>{ingredient}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default ProductDetails
