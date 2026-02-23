import React from 'react'

/**
 * Product image component with error handling
 */
function ProductImage({ imageUrl, productName }) {
  // Use a tiny inline image so we don't depend on external placeholder (avoids blocked requests / "hostname not found" errors)
  const FALLBACK_SRC = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"><rect fill="#eee" width="300" height="200"/><text fill="#999" x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="14">No image</text></svg>')
  const handleImageError = (e) => {
    e.target.src = FALLBACK_SRC
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
