/**
 * ToolShoppe ERP - Core HTTP API Client
 * Wraps browser native fetch with automatic JWT authentication,
 * error handling, and JSON response unboxing.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export function getToken() {
  try {
    return localStorage.getItem('token') || ''
  } catch {
    return ''
  }
}

export function setToken(token) {
  try {
    if (token) {
      localStorage.setItem('token', token)
    } else {
      localStorage.removeItem('token')
    }
  } catch {
    /* quota/browser sandbox ignore */
  }
}

let authPromise = null

export async function ensureAuthToken() {
  const existingToken = getToken()
  if (existingToken) return existingToken

  if (authPromise) return authPromise

  authPromise = (async () => {
    try {
      const url = `${API_BASE}/api/v1/auth/login`
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'admin', password: 'admin123' }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data && data.access_token) {
          setToken(data.access_token)
          return data.access_token
        }
      }
    } catch (err) {
      console.warn('Auto-auth attempt error:', err)
    } finally {
      authPromise = null
    }
    return ''
  })()

  return authPromise
}

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`)
    return res.ok
  } catch {
    return false
  }
}

export async function request(path, options = {}, isRetry = false) {
  const isAuthOrHealth = path.includes('/auth/login') || path.includes('/health')

  // Auto-acquire token if missing for protected routes
  if (!isAuthOrHealth && !getToken()) {
    await ensureAuthToken()
  }

  let url = path.startsWith('http') ? path : `${API_BASE}${path}`

  if (options.params && typeof options.params === 'object') {
    const searchParams = new URLSearchParams()
    for (const [key, value] of Object.entries(options.params)) {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value))
      }
    }
    const queryString = searchParams.toString()
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString
    }
  }

  const headers = new Headers(options.headers || {})

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const token = getToken()
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const { params: _, ...restOptions } = options
  const config = {
    ...restOptions,
    headers,
  }

  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body)
  }

  try {
    const response = await fetch(url, config)

    // Handle 204 No Content
    if (response.status === 204) {
      return null
    }

    // Auto-retry once on 401 Unauthorized by obtaining a fresh token
    if (response.status === 401 && !isRetry && !isAuthOrHealth) {
      setToken(null)
      const newToken = await ensureAuthToken()
      if (newToken) {
        return request(path, options, true)
      }
    }

    const contentType = response.headers.get('content-type') || ''
    const isJson = contentType.includes('application/json')
    const payload = isJson ? await response.json() : await response.text()

    if (!response.ok) {
      const errorMsg =
        (isJson && payload && (payload.message || payload.detail)) ||
        `Request failed with status ${response.status}`
      throw new ApiError(errorMsg, response.status, payload)
    }

    // Unbox standard FastAPI SuccessResponse { success: true, message: ..., data: ... }
    if (isJson && payload && typeof payload === 'object' && 'data' in payload) {
      return payload.data
    }

    return payload
  } catch (err) {
    if (err instanceof ApiError) throw err
    throw new ApiError(err.message || 'Network error connecting to backend server', 0, null)
  }
}

export const api = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body }),
  put: (path, body, options) => request(path, { ...options, method: 'PUT', body }),
  patch: (path, body, options) => request(path, { ...options, method: 'PATCH', body }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
}

export default api
