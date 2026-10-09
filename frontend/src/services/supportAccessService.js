import apiClient from './apiClient'
import { getPage } from './paging'

const BASE = '/platform-admin/company'

// What the company's CEO sees: requests made about THIS company, and the log of what was read.
export const getAccessRequestsPage = (page = 1) => getPage(`${BASE}/access-requests/`, { page })
export const getAccessLogPage = (page = 1) => getPage(`${BASE}/access-log/`, { page })

export async function approveAccessRequest(id, hours) {
  const res = await apiClient.post(`${BASE}/access-requests/${id}/approve/`, { duration_hours: hours })
  return res.data
}

export async function denyAccessRequest(id) {
  const res = await apiClient.post(`${BASE}/access-requests/${id}/deny/`)
  return res.data
}

export async function revokeAccessRequest(id) {
  const res = await apiClient.post(`${BASE}/access-requests/${id}/revoke/`)
  return res.data
}
