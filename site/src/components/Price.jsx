import React from 'react'

/**
 * Displays product price. When no store is selected (sale is null), shows the normal price.
 * When a store is selected and the product has a sale (sale.percent_off), shows the original
 * price struck through and the sale price with an "On sale" indicator.
 */
function Price({ product, sale }) {
  const price = product.price
  const percentOff = sale ? Number(sale.percent_off) : 0
  const hasSale = percentOff > 0
  const salePrice = hasSale
    ? Math.round(price * (1 - percentOff / 100) * 100) / 100
    : price

  if (hasSale) {
    return (
      <div className="product-price product-price--sale">
        <span className="product-price-original" aria-hidden="true">
          ${price.toFixed(2)}
        </span>
        <span className="product-price-current">
          ${salePrice.toFixed(2)}
        </span>
        <span className="product-price-badge">On sale ({percentOff}% off)</span>
      </div>
    )
  }

  return (
    <div className="product-price">
      <span className="product-price-current">${price.toFixed(2)}</span>
    </div>
  )
}

export default Price
