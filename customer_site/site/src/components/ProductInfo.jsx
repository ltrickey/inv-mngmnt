import React from 'react'
import ProductDetails from './ProductDetails'
import StoreStock from './StoreStock'

/**
 * Product information section component.
 * Price comes from store row (products_by_store); if no store selected, shows placeholder.
 */
function ProductInfo({ product, storeStock, storeName, storeRow, sale }) {
  const basePrice = storeRow?.price ?? product.price
  const isOnSale = basePrice != null && sale?.percent_off != null && sale.percent_off > 0
  const salePrice = isOnSale ? basePrice * (1 - sale.percent_off / 100) : basePrice
  const displayPrice = salePrice != null ? Number(salePrice).toFixed(2) : null
  const originalPriceStr = basePrice != null ? Number(basePrice).toFixed(2) : null

  return (
    <div className="product-info">
      <div className="product-name">{product.name}</div>
      <div className="product-price">
        {displayPrice != null ? (
          <>
            ${displayPrice}
            {isOnSale && originalPriceStr && (
              <>
                {' '}
                <span className="product-price-original">${originalPriceStr}</span>
                {' '}
                <span className="product-sale-badge">{sale.percent_off}% off</span>
              </>
            )}
          </>
        ) : (
          <span className="product-price-placeholder">Select a store for pricing and stock</span>
        )}
      </div>
      {product.description && <div className="product-description">{product.description}</div>}
      <ProductDetails product={product} />
      <StoreStock product={product} storeStock={storeStock} storeName={storeName} />
    </div>
  )
}

export default ProductInfo
