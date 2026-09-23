import apiClient from './apiClient'

export async function login(email, password) {
  const response = await apiClient.post('/auth/login/', { email, password })
  const { access, refresh } = response.data
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
  return response.data
}

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

export function isAuthenticated() {
  return !!localStorage.getItem('access_token')
}

export async function getMe() {
  const response = await apiClient.get('/auth/me/')
  return response.data.data
}