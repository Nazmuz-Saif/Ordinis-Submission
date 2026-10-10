import { useCallback, useEffect, useState } from 'react'

// Loads one page of a paginated list and can reload it.
// load(page) must return { items, count, pageSize, totalPages }. Pass `key` (a filter value) to restart from page 1.
export function usePagedList(load, key = '') {
  const [state, setState] = useState({ key, page: 1 })
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  // a changed filter means "go back to page 1"
  const page = state.key === key ? state.page : 1
  const setPage = useCallback((next) => setState({ key, page: next }), [key])

  useEffect(() => {
    let active = true
    load(page)
      .then((result) => {
        if (!active) return
        setData(result)
        setError('')
      })
      .catch((err) => {
        if (!active) return
        if (err.response?.status === 404 && page > 1) setPage(page - 1)
        else setError(err.response?.data?.error?.message || 'Failed to load.')
      })
    return () => {
      active = false
    }
  }, [load, page, refresh, setPage])

  const reload = useCallback(() => setRefresh((n) => n + 1), [])
  return { data, error, page, setPage, reload, loading: !data && !error }
}
