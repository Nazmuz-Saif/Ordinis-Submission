import apiClient from './apiClient'

export async function getPermissions() {
  const res = await apiClient.get('/rbac/permissions/')
  return res.data
}

export async function getRoles() {
  const res = await apiClient.get('/rbac/roles/')
  return res.data
}

export async function createRole(payload) {
  const res = await apiClient.post('/rbac/roles/', payload)
  return res.data
}

export async function updateRole(id, payload) {
  const res = await apiClient.put(`/rbac/roles/${id}/`, payload)
  return res.data
}

export async function deleteRole(id) {
  const res = await apiClient.delete(`/rbac/roles/${id}/`)
  return res.data
}
