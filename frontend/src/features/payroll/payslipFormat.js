export function formatMoney(value, currency = 'BDT') {
  const amount = Number(value)
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 2 }).format(amount)
  } catch {
    return `${currency} ${amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
  }
}

// The current month as YYYY-MM, for <input type="month">.
export function currentMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export const errorText = (err, fallback) => err.response?.data?.error?.message || fallback
