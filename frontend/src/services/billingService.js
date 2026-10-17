import apiClient from './apiClient'

// Billing is read-only for the company: it can see its plan, its seats and its invoices, not change them.
export async function getSubscription() {
  const res = await apiClient.get('/billing/subscription/')
  return res.data.data
}

export async function getInvoicesPage(page = 1) {
  const res = await apiClient.get('/billing/invoices/', { params: { page, page_size: 20 } })
  const body = res.data
  return {
    items: body.data,
    count: body.pagination.count,
    page,
    pageSize: 20,
    totalPages: Math.max(1, Math.ceil(body.pagination.count / 20)),
  }
}
