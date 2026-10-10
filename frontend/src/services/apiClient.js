import axios from 'axios'

// Set VITE_API_URL in frontend/.env to point at another backend; defaults to local development.
const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Every request automatically carries the JWT access token,
// if we have one saved.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// These endpoints answer 401 for reasons that a token refresh cannot fix
// (wrong password, bad refresh token), so they are never retried.
const AUTH_PATHS = ['/auth/login/', '/auth/refresh/', '/auth/register/', '/auth/logout/']

function forceLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

// One refresh at a time: if several requests fail together, they all wait for the same refresh.
let refreshPromise = null

async function refreshAccessToken() {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) throw new Error('No refresh token')
  // Plain axios (not apiClient) so this call can never trigger the interceptor again.
  const res = await axios.post(`${BASE_URL}/auth/refresh/`, { refresh })
  localStorage.setItem('access_token', res.data.access)
  // The server rotates refresh tokens: the old one is now blacklisted, keep the new one.
  if (res.data.refresh) localStorage.setItem('refresh_token', res.data.refresh)
  return res.data.access
}

// An expired access token is renewed silently; the user is only sent to the
// login page when the refresh token itself is no longer valid.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status !== 401 || !original) return Promise.reject(error)

    const isAuthCall = AUTH_PATHS.some((p) => original.url?.includes(p))
    if (isAuthCall) return Promise.reject(error)

    if (original._retried) {
      forceLogout()
      return Promise.reject(error)
    }
    original._retried = true

    try {
      refreshPromise = refreshPromise || refreshAccessToken().finally(() => { refreshPromise = null })
      const newAccess = await refreshPromise
      original.headers.Authorization = `Bearer ${newAccess}`
      return apiClient(original)
    } catch {
      forceLogout()
      return Promise.reject(error)
    }
  }
)

export default apiClient
