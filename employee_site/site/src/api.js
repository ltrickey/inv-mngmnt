import { getIdToken } from './auth'

const BASE = import.meta.env.VITE_API_BASE_URL || ''

async function authFetch(path, options = {}) {
  const token = await getIdToken()
  const headers = { ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(options.body)
  }
  const resp = await fetch(`${BASE}${path}`, { ...options, headers })
  if (resp.status === 401) throw new Error('Unauthorized')
  if (resp.status === 204) return null
  const data = await resp.json()
  if (!resp.ok) throw new Error(data.detail || data.error || resp.statusText)
  return data
}

export const fetchStores = () => authFetch('/api/stores')
export const fetchProducts = () => authFetch('/api/products')
export const fetchInventory = (storeId) => authFetch(`/api/inventory/${storeId}`)

export const createStockItem = (storeId, barcode, body) =>
  authFetch(`/api/inventory/${storeId}/${barcode}`, { method: 'POST', body })

export const updateStockQuantity = (storeId, barcode, quantity) =>
  authFetch(`/api/inventory/${storeId}/${barcode}`, { method: 'PUT', body: { quantity } })

export const deleteStockItem = (storeId, barcode) =>
  authFetch(`/api/inventory/${storeId}/${barcode}`, { method: 'DELETE' })

export const fetchCategories = () => authFetch('/api/categories')

// Report scheduling
export const fetchSchedules = () => authFetch('/api/reports/schedules')

export const createSchedule = (body) =>
  authFetch('/api/reports/schedules', { method: 'POST', body })

export const deleteSchedule = (scheduleId) =>
  authFetch(`/api/reports/schedules/${scheduleId}`, { method: 'DELETE' })

export const fetchScheduleResults = (scheduleId) =>
  authFetch(`/api/reports/schedules/${scheduleId}/results`)

export const downloadReport = async (s3Key) => {
  const { url } = await authFetch(`/api/reports/results/download?s3_key=${encodeURIComponent(s3Key)}`)
  const a = document.createElement('a')
  a.href = url
  a.download = s3Key.split('/').pop()
  a.click()
}
