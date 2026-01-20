import React, { useState, useEffect } from 'react'
import CategoryFilter from './components/CategoryFilter'
import ProductsGrid from './components/ProductsGrid'
import Loading from './components/Loading'
import Error from './components/Error'

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

  return (
    <div className="app">
      <h1>Products Catalog</h1>

      <CategoryFilter
        categories={categories}
        selectedCategories={selectedCategories}
        onCategoryToggle={handleCategoryToggle}
      />

      {loading && <Loading />}
      {error && <Error message={error} />}

      {!loading && !error && <ProductsGrid products={products} />}
    </div>
  )
}

export default App
