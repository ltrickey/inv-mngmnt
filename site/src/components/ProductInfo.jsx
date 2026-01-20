import React from 'react'
import ProductDetails from './ProductDetails'

/**
 * Product information section component
 */
function ProductInfo({ product }) {
  return (
    <div className="product-info">
      <div className="product-name">{product.name}</div>
      <div className="product-price">${product.price.toFixed(2)}</div>
      <div className="product-description">{product.description}</div>
      <ProductDetails product={product} />
    </div>
  )
}

export default ProductInfo
