import apiClient from './apiClient'

// Every list endpoint answers one page at a time:
//   { success, data: [...], pagination: { count, next, previous } }
// These two helpers hide that from the pages.

// Reads EVERY page and returns one plain array. Use it for dropdowns and short lists
// where the page needs all items (departments, roles, employees in a select box).
export async function getAllPages(url, params = {}) {
  const items = []
  let page = 1
  for (;;) {
    const res = await apiClient.get(url, { params: { ...params, page, page_size: 100 } })
    const body = res.data
    if (Array.isArray(body)) return body // endpoint is not paginated
    items.push(...body.data)
    if (!body.pagination?.next) return items
    page += 1
  }
}

// Reads ONE page. Use it for long lists that show page controls.
export async function getPage(url, { page = 1, pageSize = 20, ...params } = {}) {
  const res = await apiClient.get(url, { params: { ...params, page, page_size: pageSize } })
  const body = res.data
  const items = Array.isArray(body) ? body : body.data
  const count = Array.isArray(body) ? body.length : body.pagination.count
  return {
    items,
    count,
    page,
    pageSize,
    totalPages: Math.max(1, Math.ceil(count / pageSize)),
  }
}
