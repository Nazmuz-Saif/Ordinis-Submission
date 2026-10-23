import apiClient from './apiClient'
import { getPage } from './paging'

const BASE = '/platform-admin/admin'

// Platform Admin panel. Never returns employee, task or salary data.
export const getCompaniesPage = (page = 1) => getPage(`${BASE}/companies/`, { page })
export const getTicketsPage = (page = 1, status = '') => getPage(`${BASE}/tickets/`, { page, ...(status ? { status } : {}) })
export const getAccessRequestsPage = (page = 1) => getPage(`${BASE}/access-requests/`, { page })
export const getActionsPage = (page = 1) => getPage(`${BASE}/actions/`, { page })

async function post(url) {
  const res = await apiClient.post(url)
  return res.data
}
export const suspendCompany = (id) => post(`${BASE}/companies/${id}/suspend/`)
export const activateCompany = (id) => post(`${BASE}/companies/${id}/activate/`)
export const resolveTicket = (id) => post(`${BASE}/tickets/${id}/resolve/`)
export const reopenTicket = (id) => post(`${BASE}/tickets/${id}/reopen/`)

// ---- Payments and subscriptions (ST-148) ----
export const getPaymentsPage = (page = 1, { status = '', method = '', q = '' } = {}) =>
  getPage(`${BASE}/payments/`, { page, ...(status ? { status } : {}), ...(method ? { method } : {}), ...(q ? { q } : {}) })
export const getSubscriptionsPage = (page = 1, { filter = '', q = '' } = {}) =>
  getPage(`${BASE}/subscriptions/`, { page, ...(filter ? { filter } : {}), ...(q ? { q } : {}) })

export async function getPendingPaymentsCount() {
  const res = await apiClient.get(`${BASE}/payments/pending-count/`)
  return res.data.data.count
}

export async function approvePayment(id) {
  const res = await apiClient.post(`${BASE}/payments/${id}/approve/`)
  return res.data
}

export async function rejectPayment(id, note) {
  const res = await apiClient.post(`${BASE}/payments/${id}/reject/`, { note })
  return res.data
}
