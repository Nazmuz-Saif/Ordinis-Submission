import apiClient from './apiClient'
import { getPage } from './paging'

const BASE = '/platform-admin/admin'

// Platform Admin panel. Never returns employee, task or salary data.
export const getCompaniesPage = (page = 1) => getPage(`${BASE}/companies/`, { page })
export const getTicketsPage = (page = 1, status = '') => getPage(`${BASE}/tickets/`, { page, ...(status ? { status } : {}) })
export const getAccessRequestsPage = (page = 1) => getPage(`${BASE}/access-requests/`, { page })
export const getActionsPage = (page = 1) => getPage(`${BASE}/actions/`, { page })

async function post(url, body) {
  const res = await apiClient.post(url, body)
  return res.data
}
// `note` is optional and goes into the platform action log.
export const suspendCompany = (id, note = '') => post(`${BASE}/companies/${id}/suspend/`, { note })
export const activateCompany = (id, note = '') => post(`${BASE}/companies/${id}/activate/`, { note })

// ST-152: one company's detail page. Contacts and counts only, never employee, task or salary data.
export async function getCompany(id) {
  const res = await apiClient.get(`${BASE}/companies/${id}/`)
  return res.data
}

// A Break-Glass request for one company; the company's CEO decides.
export async function createAccessRequest(company, reason) {
  const res = await apiClient.post('/platform-admin/requests/', { company, reason })
  return res.data
}
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
