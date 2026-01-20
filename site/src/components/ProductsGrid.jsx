import React from 'react'
import ProductCard from './ProductCard'

/**
 * Products grid container component
 */
function ProductsGrid({ products }) {
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
        <ProductCard key={`${product.barcode}-${product.barcode_type}`} product={product} />
      ))}
    </div>
  )
}

export default ProductsGrid
