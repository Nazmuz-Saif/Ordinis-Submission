// What the Billing timeline card shows, worked out from the subscription summary the server sends
// (`days_left` is the server's: end date minus the company's own today).
const DAY = 24 * 60 * 60 * 1000

function parseDay(iso) {
  return new Date(`${iso}T00:00:00`).getTime()
}

export const EXPIRING_DAYS = 7

export function timelineView(t) {
  const total = Math.max(1, Math.round((parseDay(t.period_end) - parseDay(t.period_start)) / DAY) + 1)
  const left = t.days_left
  const elapsed = left < 0 ? total : total - (left + 1)
  const percent = Math.min(100, Math.max(0, Math.round((elapsed / total) * 100)))

  let status = { key: 'active', label: 'Active', tone: 'success' }
  if (t.restricted) status = { key: 'restricted', label: 'Restricted', tone: 'failed' }
  else if (left <= EXPIRING_DAYS) status = { key: 'expiring', label: 'Expiring soon', tone: 'warning' }

  let big
  let caption
  if (t.restricted) {
    big = 'Ended'
    caption = left < 0 ? `${-left} ${-left === 1 ? 'day' : 'days'} ago` : ''
  } else if (left < 0) {
    big = 'Ended'
    caption = `${-left} ${-left === 1 ? 'day' : 'days'} ago, still working for a few days`
  } else if (left === 0) {
    big = 'Today'
    caption = 'is the last day of your plan'
  } else {
    big = String(left)
    caption = left === 1 ? 'day left' : 'days left'
  }
  return { percent, status, big, caption, total }
}
