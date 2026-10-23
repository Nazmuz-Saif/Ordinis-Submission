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

// ---- Choosing and paying for a plan (ST-147). The amount is always the server's quote. ----

export async function getPlans() {
  const res = await apiClient.get('/billing/plans/')
  return res.data
}

export async function getQuote(plan, months) {
  const res = await apiClient.get('/billing/quote/', { params: { plan, months } })
  return res.data.data
}

export async function getPaymentInstructions() {
  const res = await apiClient.get('/billing/payment-instructions/')
  return res.data.data
}

// The company's own payments, newest first.
export async function getPayments() {
  const res = await apiClient.get('/billing/payments/', { params: { page_size: 20 } })
  return res.data.data
}

export async function submitPayment(values) {
  const res = await apiClient.post('/billing/payments/', values)
  return res.data
}
