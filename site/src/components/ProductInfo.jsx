import React from 'react'
import ProductDetails from './ProductDetails'
import StoreStock from './StoreStock'

/**
 * Product information section component
 */
function ProductInfo({ product, storeStock, storeName }) {
  return (
    <div className="product-info">
      <div className="product-name">{product.name}</div>
      <div className="product-price">${product.price.toFixed(2)}</div>
      <div className="product-description">{product.description}</div>
      <ProductDetails product={product} />
      <StoreStock product={product} storeStock={storeStock} storeName={storeName} />
    </div>
  )
}

export default ProductInfo
