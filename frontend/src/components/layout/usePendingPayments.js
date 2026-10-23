import { useEffect, useState } from 'react'
import { getPendingPaymentsCount } from '../../services/adminService'

export const PAYMENTS_CHANGED = 'ordinis:payments-changed'

// The number of payments waiting for the Platform Admin. Refreshes every 30 seconds and right after a decision
// (the Payments page fires PAYMENTS_CHANGED). `enabled` is false for everyone but a Platform Admin.
export function usePendingPayments(enabled) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!enabled) return undefined
    let active = true
    const load = () =>
      getPendingPaymentsCount()
        .then((n) => {
          if (active) setCount(n)
        })
        .catch(() => {})
    load()
    const timer = setInterval(load, 30000)
    window.addEventListener(PAYMENTS_CHANGED, load)
    return () => {
      active = false
      clearInterval(timer)
      window.removeEventListener(PAYMENTS_CHANGED, load)
    }
  }, [enabled])

  return enabled ? count : 0
}
