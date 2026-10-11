import apiClient from './apiClient'
import { getAllPages, getPage } from './paging'

const BASE = '/attendance'

// ---- Leave types (everyone reads, manage_leave_types changes) ----
export const getLeaveTypes = () => getAllPages(`${BASE}/leave-types/`)

export async function createLeaveType(payload) {
  const res = await apiClient.post(`${BASE}/leave-types/`, payload)
  return res.data
}

export async function updateLeaveType(id, payload) {
  const res = await apiClient.patch(`${BASE}/leave-types/${id}/`, payload)
  return res.data
}

export async function deleteLeaveType(id) {
  await apiClient.delete(`${BASE}/leave-types/${id}/`)
}

// ---- My leave ----
export async function getLeaveBalance(year) {
  const res = await apiClient.get(`${BASE}/leave-requests/balance/`, { params: year ? { year } : {} })
  return res.data // [{ leave_type, name, year, allowed, approved, pending, remaining }]
}

export async function getLeaveRequestsPage(page = 1, status = '') {
  return getPage(`${BASE}/leave-requests/`, { page, ...(status ? { status } : {}) })
}

// payload: { leave_type, start_date, end_date, reason }. The server checks the balance and the dates.
export async function applyLeave(payload) {
  const res = await apiClient.post(`${BASE}/leave-requests/`, payload)
  return res.data
}

export async function cancelLeave(id) {
  const res = await apiClient.post(`${BASE}/leave-requests/${id}/cancel/`)
  return res.data
}
