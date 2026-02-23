import React, { useState } from 'react'
import { login, completeNewPassword } from '../auth'

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingUser, setPendingUser] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await login(username, password)
      if (result.newPasswordRequired) {
        setPendingUser(result.user)
      } else {
        onLogin()
      }
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleNewPassword = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await completeNewPassword(pendingUser, newPassword)
      onLogin()
    } catch (err) {
      setError(err.message || 'Password change failed')
    } finally {
      setLoading(false)
    }
  }

  if (pendingUser) {
    return (
      <div className="login-container">
        <h2>Set New Password</h2>
        <p>Your temporary password must be changed.</p>
        <form onSubmit={handleNewPassword}>
          <input
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : 'Set Password'}
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="login-container">
      <h2>Employee Login</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Username or email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </div>
  )
}
