import apiClient from './apiClient'
import { getAllPages } from './paging'

export async function getChains() {
  return getAllPages('/approvals/chains/')
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

export async function getInstances(mine) {
  return getAllPages('/approvals/instances/', mine ? { mine: 'pending' } : {})
}

export async function approveInstance(id, comment) {
  const res = await apiClient.post(`/approvals/instances/${id}/approve/`, { comment })
  return res.data
}

export async function rejectInstance(id, comment) {
  const res = await apiClient.post(`/approvals/instances/${id}/reject/`, { comment })
  return res.data
}

export async function getDelegations() {
  return getAllPages('/approvals/delegations/')
}

export async function createDelegation(payload) {
  const res = await apiClient.post('/approvals/delegations/', payload)
  return res.data
}

export async function deleteDelegation(id) {
  const res = await apiClient.delete(`/approvals/delegations/${id}/`)
  return res.data
}
