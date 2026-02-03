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

  // Fetch products when selected categories or categories list (for level lookup) change
  useEffect(() => {
    fetchProducts()
  }, [selectedCategories, categories])

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
      // API uses p_category (primary), s_category (secondary), t_category (tertiary) – one per level
      if (selectedCategories.length > 0 && categories.length > 0) {
        const byLevel = { primary: null, secondary: null, tertiary: null }
        for (const name of selectedCategories) {
          const cat = categories.find(c => c.name === name)
          if (cat && byLevel[cat.level] === null) {
            byLevel[cat.level] = name
          }
        }
        const params = []
        if (byLevel.primary) params.push(`p_category=${encodeURIComponent(byLevel.primary)}`)
        if (byLevel.secondary) params.push(`s_category=${encodeURIComponent(byLevel.secondary)}`)
        if (byLevel.tertiary) params.push(`t_category=${encodeURIComponent(byLevel.tertiary)}`)
        if (params.length > 0) url = `${url}?${params.join('&')}`
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
