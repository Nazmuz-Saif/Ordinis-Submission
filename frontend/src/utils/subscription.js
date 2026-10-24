// Subscription states come from /auth/me/ (`me.subscription`), computed by the server from the end date and
// the company's own today. Nothing here counts days.

// Pages that stay open while the company is restricted (a company waiting for its first payment, or past its end date + grace).
const OPEN_WHEN_RESTRICTED = ['/settings/billing', '/profile']

export function isRestricted(me) {
  return Boolean(me?.subscription?.restricted)
}

export function pathOpenWhenRestricted(pathname) {
  return OPEN_WHEN_RESTRICTED.some((p) => pathname === p || pathname.startsWith(`${p}/`))
}

// A company that registered but whose first payment is not approved yet works only through the /subscribe pages.
export function isPendingPayment(me) {
  return me?.subscription?.status === 'pending_payment'
}

export const MONTH_CHOICES = [1, 3, 6, 12]
export const MIN_MONTHS = 1
export const MAX_MONTHS = 36

export function validMonths(value) {
  const n = Number(value)
  return Number.isInteger(n) && n >= MIN_MONTHS && n <= MAX_MONTHS
}

const WARN_DAYS = 7

// What the banner should say, or null when there is nothing to say.
export function bannerFor(subscription) {
  if (!subscription) return null
  const { status, days_left: left, grace_days: grace } = subscription
  if (status === 'pending_payment') {
    return { tone: 'info', text: 'Your company is waiting for its first payment to be approved. Only Billing, your profile and support work until then.' }
  }
  if (status === 'expired') {
    return { tone: 'danger', text: 'Your subscription has ended. Only Billing, your profile and support work until you renew.' }
  }
  if (status === 'grace') {
    const ago = -left
    const remaining = Math.max((grace ?? 0) + left, 0)
    return {
      tone: 'warn',
      text: `Your plan ended ${ago} ${ago === 1 ? 'day' : 'days'} ago. Renew within ${remaining} ${remaining === 1 ? 'day' : 'days'} or the company goes into restricted mode.`,
    }
  }
  if (status === 'active' && left <= WARN_DAYS) {
    if (left === 0) return { tone: 'warn', text: 'Your plan ends today. Renew to keep using Ordinis.' }
    return { tone: 'warn', text: `Your plan ends in ${left} ${left === 1 ? 'day' : 'days'}. Renew to keep using Ordinis.` }
  }
  return null
}
