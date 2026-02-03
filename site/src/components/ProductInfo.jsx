import React from 'react'
import ProductDetails from './ProductDetails'
import StoreStock from './StoreStock'
import Price from './Price'

/**
 * Product information section component
 */
function ProductInfo({ product, storeStock, storeName, sale }) {
  return (
    <div className="product-info">
      <div className="product-name">{product.name}</div>
      <Price product={product} sale={sale} />
      <div className="product-description">{product.description}</div>
      <ProductDetails product={product} />
      <StoreStock product={product} storeStock={storeStock} storeName={storeName} />
    </div>
  )
}

export default ProductInfo
