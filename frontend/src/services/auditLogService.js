import apiClient from './apiClient'

// The Audit Log is read-only: there is no create, update or delete here on purpose.
function paramsOf(filters = {}) {
  const params = {}
  for (const key of ['module', 'action', 'status', 'q', 'date_from', 'date_to']) {
    if (filters[key]) params[key] = filters[key]
  }
  return params
}

export async function getAuditLogsPage(page = 1, filters = {}) {
  const res = await apiClient.get('/audit-log/logs/', { params: { ...paramsOf(filters), page, page_size: 20 } })
  const body = res.data
  return {
    items: body.data,
    count: body.pagination.count,
    page,
    pageSize: 20,
    totalPages: Math.max(1, Math.ceil(body.pagination.count / 20)),
  }
}

export async function getAuditModules() {
  const res = await apiClient.get('/audit-log/logs/modules/')
  const body = res.data
  return Array.isArray(body) ? body : body.data
}

// Downloads the CSV for the current filters. The request carries the login token, so a plain link would not work.
export async function downloadAuditExport(filters = {}) {
  const res = await apiClient.get('/audit-log/logs/export/', { params: paramsOf(filters), responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'audit-log.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
