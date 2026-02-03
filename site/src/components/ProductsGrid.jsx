import React from 'react'
import ProductCard from './ProductCard'

/**
 * Products grid container component
 */
function ProductsGrid({ products, storeStock, storeName, storeSales }) {
  // Look up sale once per product here; pass single sale to each card instead of full array
  if (products.length === 0) {
    return (
      <div className="no-products">
        No products found. Try selecting different categories.
      </div>
    )
  }

  return (
    <div className="products-grid">
      {products.map(product => {
        const sale = storeSales?.find(
          (s) => String(s.barcode) === String(product.barcode) && s.percent_off != null
        ) ?? null
        return (
          <ProductCard
            key={`${product.barcode}-${product.barcode_type}`}
            product={product}
            storeStock={storeStock}
            storeName={storeName}
            sale={sale}
          />
        )
      })}
    </div>
  )
}

export default ProductsGrid
