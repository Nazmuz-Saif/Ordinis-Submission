import apiClient from './apiClient'

export async function getPermissions() {
  const res = await apiClient.get('/roles/permissions/')
  return res.data
}

export async function getRoles() {
  const res = await apiClient.get('/roles/roles/')
  return res.data
}

export async function createRole(payload) {
  const res = await apiClient.post('/roles/roles/', payload)
  return res.data
}

export async function updateRole(id, payload) {
  const res = await apiClient.put(`/roles/roles/${id}/`, payload)
  return res.data
}

export async function deleteRole(id) {
  const res = await apiClient.delete(`/roles/roles/${id}/`)
  return res.data
}
