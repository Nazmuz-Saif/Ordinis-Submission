import apiClient from './apiClient'
import { getAllPages } from './paging'

export async function getPermissions() {
  return getAllPages('/rbac/permissions/')
}

export async function getRoles() {
  return getAllPages('/rbac/roles/')
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
