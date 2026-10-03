import apiClient from './apiClient'

export async function getChains() {
  const res = await apiClient.get('/approvals/chains/')
  return res.data
}

export async function createChain(payload) {
  const res = await apiClient.post('/approvals/chains/', payload)
  return res.data
}

export async function updateChain(id, payload) {
  const res = await apiClient.patch(`/approvals/chains/${id}/`, payload)
  return res.data
}

export async function deleteChain(id) {
  const res = await apiClient.delete(`/approvals/chains/${id}/`)
  return res.data
}

export async function reorderChain(id, stepIds) {
  const res = await apiClient.post(`/approvals/chains/${id}/reorder/`, { step_ids: stepIds })
  return res.data
}

export async function createStep(payload) {
  const res = await apiClient.post('/approvals/steps/', payload)
  return res.data
}

export async function deleteStep(id) {
  const res = await apiClient.delete(`/approvals/steps/${id}/`)
  return res.data
}
