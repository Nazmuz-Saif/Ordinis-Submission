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
