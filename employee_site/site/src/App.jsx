import React, { useState, useEffect, useCallback } from 'react'
import Login from './components/Login'
import StoreSelector from './components/StoreSelector'
import StockTable from './components/StockTable'
import AddProductModal from './components/AddProductModal'
import ReportsPage from './pages/ReportsPage'
import { getCurrentUser, logout, isConfigured } from './auth'
import { fetchStores, fetchProducts, fetchInventory } from './api'

function App() {
  const [loggedIn, setLoggedIn] = useState(!isConfigured() || !!getCurrentUser())
  const [activeTab, setActiveTab] = useState('inventory')
  const [stores, setStores] = useState([])
  const [storesLoading, setStoresLoading] = useState(false)
  const [selectedStoreId, setSelectedStoreId] = useState(null)
  const [inventory, setInventory] = useState([])
  const [products, setProducts] = useState([])
  const [invLoading, setInvLoading] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [error, setError] = useState('')

  const loadStores = useCallback(async () => {
    setStoresLoading(true)
    try {
      setStores(await fetchStores())
    } catch (e) {
      setError(e.message)
    } finally {
      setStoresLoading(false)
    }
  }, [])

  const loadProducts = useCallback(async () => {
    try {
      setProducts(await fetchProducts())
    } catch (e) {
      setError(e.message)
    }
  }, [])

  const loadInventory = useCallback(async () => {
    if (!selectedStoreId) {
      setInventory([])
      return
    }
    setInvLoading(true)
    setError('')
    try {
      setInventory(await fetchInventory(selectedStoreId))
    } catch (e) {
      setError(e.message)
      setInventory([])
    } finally {
      setInvLoading(false)
    }
  }, [selectedStoreId])

  useEffect(() => {
    if (loggedIn) {
      loadStores()
      loadProducts()
    }
  }, [loggedIn, loadStores, loadProducts])

  useEffect(() => {
    if (loggedIn) loadInventory()
  }, [loggedIn, loadInventory])

  const handleLogout = () => {
    logout()
    setLoggedIn(false)
    setStores([])
    setInventory([])
    setProducts([])
    setSelectedStoreId(null)
  }

  if (!loggedIn) {
    return <Login onLogin={() => setLoggedIn(true)} />
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Inventory Manager</h1>
        <nav className="tab-nav">
          <button
            className={`btn ${activeTab === 'inventory' ? 'btn-add' : ''}`}
            onClick={() => setActiveTab('inventory')}
          >
            Inventory
          </button>
          <button
            className={`btn ${activeTab === 'reports' ? 'btn-add' : ''}`}
            onClick={() => setActiveTab('reports')}
          >
            Reports
          </button>
        </nav>
        <button onClick={handleLogout} className="btn btn-logout">Sign Out</button>
      </header>

      {activeTab === 'reports' ? (
        <ReportsPage />
      ) : (
        <>
          <StoreSelector
            stores={stores}
            selectedStoreId={selectedStoreId}
            onChange={setSelectedStoreId}
            loading={storesLoading}
          />

          {error && <p className="error">{error}</p>}

          {selectedStoreId && (
            <>
              <div className="toolbar">
                <button onClick={() => setShowAdd(true)} className="btn btn-add">
                  + Add Product
                </button>
                <button onClick={loadInventory} className="btn" disabled={invLoading}>
                  Refresh
                </button>
              </div>

              {invLoading ? (
                <p>Loading inventory...</p>
              ) : (
                <StockTable
                  inventory={inventory}
                  products={products}
                  onRefresh={loadInventory}
                />
              )}
            </>
          )}

          {showAdd && (
            <AddProductModal
              products={products}
              inventory={inventory}
              storeId={selectedStoreId}
              onClose={() => setShowAdd(false)}
              onRefresh={loadInventory}
            />
          )}
        </>
      )}
    </div>
  )
}

export default App
