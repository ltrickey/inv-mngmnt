import React, { useState, useEffect } from 'react'

// Use relative URLs to go through Vite proxy
const API_BASE_URL = ''

function App() {
  const [categories, setCategories] = useState([])
  const [selectedCategories, setSelectedCategories] = useState([])
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch available categories on component mount
  useEffect(() => {
    fetchCategories()
  }, [])

  // Fetch products when selected categories change
  useEffect(() => {
    fetchProducts()
  }, [selectedCategories])

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/categories`)
      if (!response.ok) {
        throw new Error('Failed to fetch categories')
      }
      const data = await response.json()
      setCategories(data)
      setLoading(false)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const fetchProducts = async () => {
    try {
      setLoading(true)
      let url = `${API_BASE_URL}/products`
      
      if (selectedCategories.length > 0) {
        const categoryParams = selectedCategories
          .map(cat => `category=${encodeURIComponent(cat)}`)
          .join('&')
        url = `${url}?${categoryParams}`
      }

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('Failed to fetch products')
      }
      const data = await response.json()
      setProducts(data)
      setLoading(false)
      setError(null)
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  const handleCategoryToggle = (categoryName) => {
    setSelectedCategories(prev => {
      if (prev.includes(categoryName)) {
        return prev.filter(cat => cat !== categoryName)
      } else {
        return [...prev, categoryName]
      }
    })
  }

  // Group categories by level for display
  const groupedCategories = {
    primary: categories.filter(cat => cat.level === 'primary'),
    secondary: categories.filter(cat => cat.level === 'secondary'),
    tertiary: categories.filter(cat => cat.level === 'tertiary')
  }

  return (
    <div className="app">
      <h1>Products Catalog</h1>

      <div className="filter-section">
        <h2>Filter by Category</h2>
        
        {groupedCategories.primary.length > 0 && (
          <div className="category-group">
            <h3 className="category-group-title">Primary Categories</h3>
            <div className="category-filters">
              {groupedCategories.primary.map(category => (
                <label key={category.name} className="category-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(category.name)}
                    onChange={() => handleCategoryToggle(category.name)}
                  />
                  {category.name}
                </label>
              ))}
            </div>
          </div>
        )}

        {groupedCategories.secondary.length > 0 && (
          <div className="category-group">
            <h3 className="category-group-title">Secondary Categories</h3>
            <div className="category-filters">
              {groupedCategories.secondary.map(category => (
                <label key={category.name} className="category-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(category.name)}
                    onChange={() => handleCategoryToggle(category.name)}
                  />
                  {category.name}
                </label>
              ))}
            </div>
          </div>
        )}

        {groupedCategories.tertiary.length > 0 && (
          <div className="category-group">
            <h3 className="category-group-title">Tertiary Categories</h3>
            <div className="category-filters">
              {groupedCategories.tertiary.map(category => (
                <label key={category.name} className="category-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedCategories.includes(category.name)}
                    onChange={() => handleCategoryToggle(category.name)}
                  />
                  {category.name}
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {loading && <div className="loading">Loading products...</div>}
      {error && <div className="error">Error: {error}</div>}

      {!loading && !error && (
        <>
          {products.length === 0 ? (
            <div className="no-products">
              No products found. Try selecting different categories.
            </div>
          ) : (
            <div className="products-grid">
              {products.map(product => (
                <div key={`${product.barcode}-${product.barcode_type}`} className="product-card">
                  <img
                    src={product.image_url}
                    alt={product.name}
                    className="product-image"
                    onError={(e) => {
                      e.target.src = 'https://via.placeholder.com/300x200?text=No+Image'
                    }}
                  />
                  <div className="product-info">
                    <div className="product-name">{product.name}</div>
                    <div className="product-price">${product.price.toFixed(2)}</div>
                    <div className="product-description">{product.description}</div>
                    
                    <div className="product-details">
                      <div className="detail-row">
                        <span className="detail-label">Barcode:</span>
                        <span className="detail-value">{product.barcode} ({product.barcode_type})</span>
                      </div>
                      
                      <div className="detail-row">
                        <span className="detail-label">Primary Category:</span>
                        <span className="detail-value">{product.primary_category}</span>
                      </div>
                      
                      {product.secondary_category && (
                        <div className="detail-row">
                          <span className="detail-label">Secondary Category:</span>
                          <span className="detail-value">{product.secondary_category}</span>
                        </div>
                      )}
                      
                      {product.tertiary_category && (
                        <div className="detail-row">
                          <span className="detail-label">Tertiary Category:</span>
                          <span className="detail-value">{product.tertiary_category}</span>
                        </div>
                      )}
                      
                      <div className="detail-row">
                        <span className="detail-label">Ingredients:</span>
                        <ul className="ingredients-list">
                          {product.ingredients.map((ingredient, index) => (
                            <li key={index}>{ingredient}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default App
