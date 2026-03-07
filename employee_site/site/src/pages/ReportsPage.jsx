import React, { useState, useEffect, useCallback } from 'react'
import {
  fetchSchedules,
  fetchStores,
  fetchCategories,
  createSchedule,
  deleteSchedule,
  fetchScheduleResults,
  downloadReport,
} from '../api'

const FILTER_TYPES = ['store', 'category']
const FREQUENCIES = ['minute', 'hour', 'day', 'week']
const LOOKBACK_WINDOWS = ['hour', 'day', 'week']

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, { timeZoneName: 'short' })
}

function NewScheduleForm({ stores, categories, onCreated, onCancel }) {
  const [filterType, setFilterType] = useState('store')
  const [filterValue, setFilterValue] = useState('')
  const [frequency, setFrequency] = useState('hour')
  const [lookbackWindow, setLookbackWindow] = useState('day')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Reset filter value when switching between store/category
  const handleFilterTypeChange = (e) => {
    setFilterType(e.target.value)
    setFilterValue('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const schedule = await createSchedule({
        filter_type: filterType,
        filter_value: filterValue,
        frequency,
        lookback_window: lookbackWindow,
      })
      onCreated(schedule)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const primaryCategories = categories.filter((c) => c.level === 'primary')

  return (
    <form className="report-form" onSubmit={handleSubmit}>
      <h3>New Report Schedule</h3>
      {error && <p className="error">{error}</p>}
      <div className="form-row">
        <label>Filter by</label>
        <select value={filterType} onChange={handleFilterTypeChange}>
          {FILTER_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label>{filterType === 'store' ? 'Store' : 'Category'}</label>
        {filterType === 'store' ? (
          <select value={filterValue} onChange={(e) => setFilterValue(e.target.value)} required>
            <option value="">— select a store —</option>
            {stores.map((s) => (
              <option key={s.store_id} value={s.store_id}>
                {s.store_name} ({s.store_id})
              </option>
            ))}
          </select>
        ) : (
          <select value={filterValue} onChange={(e) => setFilterValue(e.target.value)} required>
            <option value="">— select a category —</option>
            {primaryCategories.map((c) => (
              <option key={c.name} value={c.name}>{c.name}</option>
            ))}
          </select>
        )}
      </div>
      <div className="form-row">
        <label>Frequency</label>
        <select value={frequency} onChange={(e) => setFrequency(e.target.value)}>
          {FREQUENCIES.map((f) => (
            <option key={f} value={f}>Every {f}</option>
          ))}
        </select>
      </div>
      <div className="form-row">
        <label>Lookback window</label>
        <select value={lookbackWindow} onChange={(e) => setLookbackWindow(e.target.value)}>
          {LOOKBACK_WINDOWS.map((w) => (
            <option key={w} value={w}>Previous {w}</option>
          ))}
        </select>
      </div>
      <div className="form-actions">
        <button type="submit" className="btn btn-add" disabled={submitting || !filterValue}>
          {submitting ? 'Creating...' : 'Create Schedule'}
        </button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

function ResultsPanel({ schedule, onClose }) {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(null)

  useEffect(() => {
    fetchScheduleResults(schedule.schedule_id)
      .then(setResults)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [schedule.schedule_id])

  const handleDownload = async (s3Key) => {
    setDownloading(s3Key)
    try {
      await downloadReport(s3Key)
    } catch (e) {
      setError(e.message)
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="results-panel">
      <div className="results-header">
        <h3>
          Results — {schedule.filter_type}: {schedule.filter_value}
        </h3>
        <button className="btn" onClick={onClose}>Close</button>
      </div>
      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Loading results...</p>
      ) : results.length === 0 ? (
        <p>No reports generated yet.</p>
      ) : (
        <table className="stock-table">
          <thead>
            <tr>
              <th>Generated At</th>
              <th>Rows</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.generated_at}>
                <td>{formatDate(r.generated_at)}</td>
                <td>{r.row_count}</td>
                <td>
                  <button
                    className="btn btn-add"
                    onClick={() => handleDownload(r.s3_key)}
                    disabled={downloading === r.s3_key}
                  >
                    {downloading === r.s3_key ? 'Downloading...' : 'Download CSV'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function ReportsPage() {
  const [schedules, setSchedules] = useState([])
  const [stores, setStores] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [activeResults, setActiveResults] = useState(null) // schedule object

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [scheduleList, storeList, categoryList] = await Promise.all([
        fetchSchedules(),
        fetchStores(),
        fetchCategories(),
      ])
      setSchedules(scheduleList)
      setStores(storeList)
      setCategories(categoryList)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreated = (schedule) => {
    setSchedules((prev) => [schedule, ...prev])
    setShowForm(false)
  }

  const handleDelete = async (scheduleId) => {
    try {
      await deleteSchedule(scheduleId)
      setSchedules((prev) => prev.filter((s) => s.schedule_id !== scheduleId))
      if (activeResults?.schedule_id === scheduleId) setActiveResults(null)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <div className="toolbar">
        <button className="btn btn-add" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancel' : '+ New Schedule'}
        </button>
        <button className="btn" onClick={load} disabled={loading}>Refresh</button>
      </div>

      {error && <p className="error">{error}</p>}

      {showForm && (
        <NewScheduleForm
          stores={stores}
          categories={categories}
          onCreated={handleCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      {loading ? (
        <p>Loading schedules...</p>
      ) : schedules.length === 0 ? (
        <p>No report schedules yet. Create one above.</p>
      ) : (
        <table className="stock-table">
          <thead>
            <tr>
              <th>Filter</th>
              <th>Value</th>
              <th>Frequency</th>
              <th>Lookback</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {schedules.map((s) => (
              <tr key={s.schedule_id}>
                <td>{s.filter_type}</td>
                <td>{s.filter_value}</td>
                <td>Every {s.frequency}</td>
                <td>Previous {s.lookback_window}</td>
                <td>{formatDate(s.created_at)}</td>
                <td className="action-cell">
                  <button
                    className="btn"
                    onClick={() =>
                      setActiveResults((prev) =>
                        prev?.schedule_id === s.schedule_id ? null : s
                      )
                    }
                  >
                    Results
                  </button>
                  <button
                    className="btn btn-delete"
                    onClick={() => handleDelete(s.schedule_id)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {activeResults && (
        <ResultsPanel
          schedule={activeResults}
          onClose={() => setActiveResults(null)}
        />
      )}
    </div>
  )
}
