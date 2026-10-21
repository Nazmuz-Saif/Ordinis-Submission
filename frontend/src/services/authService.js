import apiClient from './apiClient'

export async function login(email, password) {
  const response = await apiClient.post('/auth/login/', { email, password })
  const { access, refresh } = response.data
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
  return response.data
}

export function logout() {
  const refresh = localStorage.getItem('refresh_token')
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  // Tell the server to blacklist the refresh token so it cannot be used again.
  // Best effort: the user is logged out locally either way.
  if (refresh) {
    apiClient.post('/auth/logout/', { refresh }).catch(() => {})
  }
}

export function isAuthenticated() {
  return !!localStorage.getItem('access_token')
}

export async function getMe() {
  const response = await apiClient.get('/auth/me/')
  return response.data.data
}

export async function registerCompany(payload) {
  const response = await apiClient.post('/auth/register/', payload)
  const { access, refresh } = response.data.data
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
  return response.data.data
}

// The logged-in person's own profile. There is no id: the server only ever returns the caller's own data.
export async function getProfile() {
  const response = await apiClient.get('/auth/profile/')
  return response.data.data
}

export async function updateProfile(values) {
  const response = await apiClient.patch('/auth/profile/', values)
  return response.data.data
}
