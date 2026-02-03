import React from 'react'
import ProductCard from './ProductCard'

/**
 * Products grid container component
 */
function ProductsGrid({ products, storeStock, storeName }) {
  if (products.length === 0) {
    return (
      <div className="no-products">
        No products found. Try selecting different categories.
      </div>
    )
  }

  return (
    <div className="products-grid">
      {products.map(product => (
        <ProductCard
          key={`${product.barcode}-${product.barcode_type}`}
          product={product}
          storeStock={storeStock}
          storeName={storeName}
        />
      ))}
    </div>
  )
}

export default ProductsGrid
