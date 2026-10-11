// Calendar days from start to end with both counted. Works on YYYY-MM-DD text, so time zones cannot shift it.
export function daysBetween(start, end) {
  if (!start || !end) return null
  const toDay = (s) => {
    const [y, m, d] = s.split('-').map(Number)
    return Date.UTC(y, m - 1, d) / 86400000
  }
  return toDay(end) - toDay(start) + 1
}

export const plural = (n) => `${n} day${n === 1 ? '' : 's'}`

export const errorText = (err, fallback) => err.response?.data?.error?.message || fallback

export const STATUS = {
  pending: { variant: 'warning', label: 'Pending' },
  approved: { variant: 'success', label: 'Approved' },
  rejected: { variant: 'failed', label: 'Rejected' },
  cancelled: { variant: 'neutral', label: 'Cancelled' },
}
