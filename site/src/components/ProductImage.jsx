import React from 'react'

/**
 * Product image component with error handling
 */
function ProductImage({ imageUrl, productName }) {
  const handleImageError = (e) => {
    e.target.src = 'https://via.placeholder.com/300x200?text=No+Image'
  }

  return (
    <img
      src={imageUrl}
      alt={productName}
      className="product-image"
      onError={handleImageError}
    />
  )
}

export default ProductImage
