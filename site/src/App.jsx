import React, { useState, useEffect, useMemo } from 'react'
import CategoryFilter from './components/CategoryFilter'
import ProductsGrid from './components/ProductsGrid'
import Loading from './components/Loading'
import Error from './components/Error'

// Use relative URLs to go through Vite proxy
const API_BASE_URL = ''

/** Build { primary: { secondary: [tertiary, ...] } } from product list */
function buildCategoryHierarchy(products) {
  const hierarchy = {}
  if (!products || !products.length) return hierarchy
  products.forEach((p) => {
    const pri = p.primary_category
    const sec = p.secondary_category
    const ter = p.tertiary_category
    if (!pri) return
    if (!hierarchy[pri]) hierarchy[pri] = {}
    if (sec) {
      if (!hierarchy[pri][sec]) hierarchy[pri][sec] = []
      if (ter && !hierarchy[pri][sec].includes(ter)) hierarchy[pri][sec].push(ter)
    }
  })
  return hierarchy
}

function App() {
  const [categoryHierarchy, setCategoryHierarchy] = useState({})
  const [selectedPrimary, setSelectedPrimary] = useState('')
  const [selectedSecondary, setSelectedSecondary] = useState('')
  const [selectedTertiary, setSelectedTertiary] = useState('')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Fetch products when dropdown selections change; build hierarchy from unfiltered result when no filter applied
  useEffect(() => {
    fetchProducts()
  }, [selectedPrimary, selectedSecondary, selectedTertiary])

  const fetchProducts = async () => {
    try {
      setLoading(true)
      let url = `${API_BASE_URL}/products`
      const params = []
      if (selectedPrimary) params.push(`p_category=${encodeURIComponent(selectedPrimary)}`)
      if (selectedSecondary) params.push(`s_category=${encodeURIComponent(selectedSecondary)}`)
      if (selectedTertiary) params.push(`t_category=${encodeURIComponent(selectedTertiary)}`)
      if (params.length > 0) url = `${url}?${params.join('&')}`

      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch products')
      const data = await response.json()
      setProducts(data)
      setError(null)
      // When we fetched with no filter, use result to build category hierarchy for dropdowns
      if (params.length === 0) {
        setCategoryHierarchy(buildCategoryHierarchy(data))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handlePrimaryChange = (value) => {
    setSelectedPrimary(value || '')
    setSelectedSecondary('')
    setSelectedTertiary('')
  }
  const handleSecondaryChange = (value) => {
    setSelectedSecondary(value || '')
    setSelectedTertiary('')
  }
  const handleTertiaryChange = (value) => {
    setSelectedTertiary(value || '')
  }

  const primaryOptions = useMemo(() => Object.keys(categoryHierarchy).sort(), [categoryHierarchy])
  const secondaryOptions = useMemo(
    () => (selectedPrimary && categoryHierarchy[selectedPrimary] ? Object.keys(categoryHierarchy[selectedPrimary]).sort() : []),
    [categoryHierarchy, selectedPrimary]
  )
  const tertiaryOptions = useMemo(
    () =>
      selectedPrimary && selectedSecondary && categoryHierarchy[selectedPrimary]?.[selectedSecondary]
        ? [...categoryHierarchy[selectedPrimary][selectedSecondary]].filter(Boolean).sort()
        : [],
    [categoryHierarchy, selectedPrimary, selectedSecondary]
  )

  // Clear selectedTertiary when the tertiary dropdown is hidden or selection is no longer valid,
  // so the filter state never drifts from what the user can see or change.
  useEffect(() => {
    if (
      tertiaryOptions.length === 0 ||
      (selectedTertiary && !tertiaryOptions.includes(selectedTertiary))
    ) {
      setSelectedTertiary('')
    }
  }, [tertiaryOptions, selectedTertiary])

  return (
    <div className="app">
      <h1>Products Catalog</h1>

      <CategoryFilter
        primaryOptions={primaryOptions}
        secondaryOptions={secondaryOptions}
        tertiaryOptions={tertiaryOptions}
        selectedPrimary={selectedPrimary}
        selectedSecondary={selectedSecondary}
        selectedTertiary={selectedTertiary}
        onPrimaryChange={handlePrimaryChange}
        onSecondaryChange={handleSecondaryChange}
        onTertiaryChange={handleTertiaryChange}
      />

      {loading && <Loading />}
      {error && <Error message={error} />}

      {!loading && !error && <ProductsGrid products={products} />}
    </div>
  )
}

export default App
