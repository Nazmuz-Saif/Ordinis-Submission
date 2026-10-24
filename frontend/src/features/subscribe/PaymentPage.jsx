import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { getPaymentInstructions, getQuote } from '../../services/billingService'
import { validMonths } from '../../utils/subscription'
import { readError } from '../../utils/apiError'
import PaymentForm from '../../components/billing/PaymentForm'
import { formatMoney } from '../payroll/payslipFormat'
import SubscribeShell from './SubscribeShell'
import { formatDate, monthsText } from './subscribeFormat'

// The plan and the months live in the address (?plan=&months=), so a reload keeps the order.
function PaymentPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const plan = params.get('plan') || ''
  const months = Number(params.get('months'))
  const valid = Boolean(plan) && validMonths(months)
  const [quote, setQuote] = useState(null)
  const [instructions, setInstructions] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!valid) return
    Promise.all([getQuote(plan, months), getPaymentInstructions()])
      .then(([q, i]) => {
        setQuote(q)
        setInstructions(i)
      })
      .catch((err) => setError(readError(err, 'Could not load the payment details.').message))
  }, [valid, plan, months])

  if (!valid) return <Navigate to="/subscribe/plan" replace />

  return (
    <SubscribeShell
      step="pay"
      title="Pay and send the details"
      subtitle="Pay outside Ordinis, then tell us how. The platform team checks the payment by hand and starts your plan."
    >
      {error && (
        <div className="space-y-3">
          <p role="alert" data-testid="payment-load-error" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] text-sm px-4 py-3">{error}</p>
          <Link to="/subscribe/plan" className="text-sm text-[#6C31D6] font-medium hover:underline">Back to plans</Link>
        </div>
      )}
      {!error && !quote && <div className="skeleton h-64 rounded-xl" />}
      {quote && instructions && (
        <div className="grid gap-6 md:grid-cols-3">
          <div data-testid="order-summary" className="md:col-span-1 bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5 h-fit">
            <p className="text-sm text-[#71717A]">Your order</p>
            <p data-testid="order-plan" className="text-lg font-bold text-[#14142B] mt-1">{quote.plan.name}</p>
            <p data-testid="order-months" className="text-sm text-[#14142B]">{monthsText(quote.months)}</p>
            <p data-testid="order-total" className="text-2xl font-bold text-[#14142B] mt-3">{formatMoney(quote.amount, quote.currency)}</p>
            {Number(quote.discount) > 0 && <p className="text-xs text-[#15803D]">Includes a saving of {formatMoney(quote.discount, quote.currency)}</p>}
            <p className="text-xs text-[#71717A] mt-3">Starts {formatDate(quote.period_start)}, ends {formatDate(quote.period_end)} after approval.</p>
            <Link to="/subscribe/plan" data-testid="change-plan" className="inline-block mt-4 text-sm text-[#6C31D6] font-medium hover:underline">Change plan or months</Link>
          </div>
          <div className="md:col-span-2 bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
            <PaymentForm
              quote={quote}
              instructions={instructions}
              onSubmitted={() => navigate('/subscribe/waiting', { replace: true })}
              onAlreadyPending={() => navigate('/subscribe/waiting', { replace: true })}
            />
          </div>
        </div>
      )}
    </SubscribeShell>
  )
}

export default PaymentPage
