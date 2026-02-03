import React, { useState, useEffect, useMemo } from 'react'
import CategoryFilter from './components/CategoryFilter'
import StoreSelector from './components/StoreSelector'
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
  const [stores, setStores] = useState([])
  const [selectedStoreId, setSelectedStoreId] = useState(null)
  const [storesLoading, setStoresLoading] = useState(true)
  const [storesError, setStoresError] = useState(null)
  const [storeStock, setStoreStock] = useState([])
  const [storeSales, setStoreSales] = useState([])
  const [storeSalesError, setStoreSalesError] = useState(null)

  // Fetch stores once on mount
  useEffect(() => {
    const fetchStores = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/stores`)
        if (!response.ok) throw new Error('Failed to fetch stores')
        const data = await response.json()
        setStores(data)
        setStoresError(null)
      } catch (err) {
        setStoresError(err.message)
      } finally {
        setStoresLoading(false)
      }
    }
    fetchStores()
  }, [])

  // Fetch stock for selected store when store selection changes
  useEffect(() => {
    if (!selectedStoreId) {
      setStoreStock([])
      return
    }
    const fetchStock = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/stock/${selectedStoreId}`)
        if (!response.ok) throw new Error('Failed to fetch stock')
        const data = await response.json()
        setStoreStock(data)
      } catch (err) {
        setStoreStock([])
      }
    }
    fetchStock()
  }, [selectedStoreId])

  // Fetch sales for selected store when store selection changes (for percent_off / sale prices)
  useEffect(() => {
    if (!selectedStoreId) {
      setStoreSales([])
      setStoreSalesError(null)
      return
    }
    const fetchSales = async () => {
      try {
        setStoreSalesError(null)
        const response = await fetch(`${API_BASE_URL}/sales/${selectedStoreId}`)
        if (!response.ok) throw new Error(`Sales: ${response.status} ${response.statusText}`)
        const data = await response.json()
        setStoreSales(Array.isArray(data) ? data : [])
      } catch (err) {
        setStoreSales([])
        setStoreSalesError(err.message || 'Failed to load sales')
      }
    }
    fetchSales()
  }, [selectedStoreId])

  // Fetch products when dropdown selections change; build hierarchy from unfiltered result when no filter applied
  useEffect(() => {
    fetchProducts()
  }, [selectedPrimary, selectedSecondary, selectedTertiary, selectedStoreId])

  const fetchProducts = async () => {
    try {
      setLoading(true)
      let url = `${API_BASE_URL}/products`
      // Only send the most specific category filter (categories are nested):
      // t_category > s_category > p_category
      const params = []
      if (selectedTertiary) {
        params.push(`t_category=${encodeURIComponent(selectedTertiary)}`)
      } else if (selectedSecondary) {
        params.push(`s_category=${encodeURIComponent(selectedSecondary)}`)
      } else if (selectedPrimary) {
        params.push(`p_category=${encodeURIComponent(selectedPrimary)}`)
      }
      if (params.length > 0) url = `${url}?${params[0]}`

      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch products')
      const data = await response.json()
      setProducts(data)
      setError(null)
      // When we fetched with no filter, use result to build category hierarchy for dropdowns.
      // If a store is selected and stock is loaded, build the hierarchy from that store's available products.
      if (params.length === 0) {
        const storeBarcodes = selectedStoreId && Array.isArray(storeStock)
          ? new Set(storeStock.map((s) => String(s.barcode)))
          : null
        const hierarchySource = storeBarcodes
          ? data.filter((p) => storeBarcodes.has(String(p.barcode)))
          : data
        setCategoryHierarchy(buildCategoryHierarchy(hierarchySource))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // When the selected store changes, reset category selections and refresh products (unfiltered),
  // then rebuild category options based on that store's inventory once stock is available.
  const handleStoreChange = (storeId) => {
    setSelectedStoreId(storeId)
    setSelectedPrimary('')
    setSelectedSecondary('')
    setSelectedTertiary('')
    setCategoryHierarchy({})
    // fetchProducts will run via the category-selection effect (after state updates),
    // and categoryHierarchy will be rebuilt once unfiltered products are loaded.
  }

  // Display only products that exist in the selected store's stock list.
  // This keeps UI aligned with "products for that store" without changing the API.
  const visibleProducts = useMemo(() => {
    if (!selectedStoreId || !Array.isArray(storeStock)) return products
    const barcodes = new Set(storeStock.map((s) => String(s.barcode)))
    return products.filter((p) => barcodes.has(String(p.barcode)))
  }, [products, selectedStoreId, storeStock])

  // If a store is selected and we have stock, rebuild the dropdown hierarchy from that store's products
  // (only when no category filter is currently applied).
  useEffect(() => {
    const hasCategoryFilter = selectedPrimary || selectedSecondary || selectedTertiary
    if (!selectedStoreId || !Array.isArray(storeStock) || hasCategoryFilter) return
    setCategoryHierarchy(buildCategoryHierarchy(visibleProducts))
  }, [selectedStoreId, storeStock, selectedPrimary, selectedSecondary, selectedTertiary, visibleProducts])

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

  const selectedStore = useMemo(
    () => (selectedStoreId ? stores.find((s) => s.store_id === selectedStoreId) : null),
    [stores, selectedStoreId]
  )
  const storeName = selectedStore ? selectedStore.store_name : null

  return (
    <div className="app">
      <h1>Products Catalog</h1>

      <StoreSelector
        stores={stores}
        selectedStoreId={selectedStoreId}
        onStoreChange={handleStoreChange}
        loading={storesLoading}
        error={storesError}
        salesError={storeSalesError}
      />

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

      {!loading && !error && (
        <ProductsGrid
          products={visibleProducts}
          storeStock={selectedStoreId ? storeStock : null}
          storeName={storeName}
          storeSales={selectedStoreId ? storeSales : null}
        />
      )}
    </div>
  )
}

export default App
