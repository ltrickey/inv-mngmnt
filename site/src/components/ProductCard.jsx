import React from 'react'
import ProductImage from './ProductImage'
import ProductInfo from './ProductInfo'

/**
 * Product card component displaying a single product
 */
function ProductCard({ product, storeStock, storeName, sale }) {
  return (
    <div className="product-card">
      <ProductImage imageUrl={product.image_url} productName={product.name} />
      <ProductInfo
        product={product}
        storeStock={storeStock}
        storeName={storeName}
        sale={sale}
      />
    </div>
  )
}

export default ProductCard
