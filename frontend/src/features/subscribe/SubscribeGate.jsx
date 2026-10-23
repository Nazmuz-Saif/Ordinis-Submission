import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { getPayments } from '../../services/billingService'

// /subscribe decides where a waiting company belongs: a payment already sent (pending or rejected) goes to the
// waiting page, a company that has not paid yet goes to the plan page.
function SubscribeGate() {
  const [target, setTarget] = useState(null)

  useEffect(() => {
    getPayments()
      .then((list) => setTarget(list[0] ? '/subscribe/waiting' : '/subscribe/plan'))
      .catch(() => setTarget('/subscribe/plan'))
  }, [])

  return target ? <Navigate to={target} replace /> : null
}

export default SubscribeGate
