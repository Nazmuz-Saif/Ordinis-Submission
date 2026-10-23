import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Clock, XCircle } from 'lucide-react'
import { getPaymentInstructions, getPayments, getQuote } from '../../services/billingService'
import { useAuth } from '../../store/AuthContext'
import PaymentForm from '../../components/billing/PaymentForm'
import { formatMoney } from '../payroll/payslipFormat'
import SubscribeShell from './SubscribeShell'
import { monthsText } from './subscribeFormat'

const REFRESH_MS = 5000

function Summary({ payment }) {
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm mt-4">
      <dt className="text-[#71717A]">Plan</dt>
      <dd data-testid="waiting-plan" className="text-[#14142B] font-medium">{payment.plan_name} for {monthsText(payment.months)}</dd>
      <dt className="text-[#71717A]">Amount</dt>
      <dd data-testid="waiting-amount" className="text-[#14142B] font-medium">{formatMoney(payment.amount, payment.currency)}</dd>
      <dt className="text-[#71717A]">Paid with</dt>
      <dd className="text-[#14142B] font-medium">{payment.method_label}</dd>
      <dt className="text-[#71717A]">Transaction id</dt>
      <dd data-testid="waiting-transaction" className="text-[#14142B] font-medium">{payment.transaction_id}</dd>
    </dl>
  )
}

// Shows where the first payment stands and refreshes itself. When the platform team approves, the company becomes
// active and SubscribeRoute sends the owner to the dashboard.
function WaitingPage() {
  const { refreshMe } = useAuth()
  const navigate = useNavigate()
  const [payments, setPayments] = useState(null)
  const [retryData, setRetryData] = useState(null)      // { id, quote, instructions } for the form after a rejection
  const reload = useRef(() => {})

  useEffect(() => {
    let active = true
    const tick = () =>
      getPayments()
        .then((list) => {
          if (active) setPayments(list)
        })
        .catch(() => {})                       // keep what is shown; the next refresh tries again
        .finally(() => refreshMe())
    reload.current = tick
    tick()
    const timer = setInterval(tick, REFRESH_MS)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [refreshMe])

  const latest = payments?.[0]
  const rejectedId = latest?.status === 'rejected' ? latest.id : null
  const rejectedPlan = latest?.plan_name
  const rejectedMonths = latest?.months
  const retry = retryData?.id === rejectedId ? retryData : null

  useEffect(() => {
    if (!rejectedId) return undefined
    let active = true
    Promise.all([getQuote(rejectedPlan, rejectedMonths), getPaymentInstructions()])
      .then(([quote, instructions]) => {
        if (active) setRetryData({ id: rejectedId, quote, instructions })
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [rejectedId, rejectedPlan, rejectedMonths])

  if (payments && !latest) return <Navigate to="/subscribe/plan" replace />

  return (
    <SubscribeShell
      step="waiting"
      title={latest?.status === 'rejected' ? 'Your payment was not accepted' : 'Waiting for approval'}
      subtitle={latest?.status === 'rejected'
        ? 'Read the note below, then send the payment details again.'
        : 'The platform team is checking your payment. This page refreshes by itself and opens your dashboard as soon as it is approved.'}
    >
      {!latest && <div className="skeleton h-40 rounded-xl" />}

      {latest?.status === 'pending' && (
        <div data-testid="waiting-card" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-6 max-w-xl">
          <div className="flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-[#F59E0B]/10 text-[#B45309] flex items-center justify-center"><Clock size={20} aria-hidden="true" /></span>
            <div>
              <p data-testid="waiting-title" className="text-lg font-bold text-[#14142B]">Waiting for approval</p>
              <p className="text-sm text-[#71717A]">Your company will start once this payment is approved.</p>
            </div>
          </div>
          <Summary payment={latest} />
          <p className="text-xs text-[#71717A] mt-4">You can close this page and come back later. Log in again and you will see the same status.</p>
        </div>
      )}

      {latest?.status === 'rejected' && (
        <div className="space-y-6 max-w-3xl">
          <div data-testid="rejected-card" className="bg-white rounded-xl border border-[#DC2626]/30 shadow-sm p-6">
            <div className="flex items-center gap-3">
              <span className="w-10 h-10 rounded-xl bg-[#DC2626]/10 text-[#B91C1C] flex items-center justify-center"><XCircle size={20} aria-hidden="true" /></span>
              <p data-testid="rejected-title" className="text-lg font-bold text-[#14142B]">Payment rejected</p>
            </div>
            <p className="text-sm text-[#71717A] mt-3">Note from the platform team:</p>
            <p data-testid="rejected-note" className="text-sm text-[#14142B] bg-[#FAFAFA] rounded-lg px-4 py-3 mt-1">{latest.review_note}</p>
            <Summary payment={latest} />
          </div>
          <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-6">
            <p className="text-base font-semibold text-[#14142B] mb-4">Send the payment details again</p>
            {retry ? (
              <PaymentForm
                key={latest.id}
                quote={retry.quote}
                instructions={retry.instructions}
                initial={{ method: latest.method, payer_name: latest.payer_name, payer_number: latest.payer_number }}
                submitLabel="Submit again"
                onSubmitted={() => reload.current()}
                onAlreadyPending={() => reload.current()}
              />
            ) : (
              <div className="skeleton h-40 rounded-xl" />
            )}
            <button type="button" data-testid="choose-another-plan" onClick={() => navigate('/subscribe/plan')} className="mt-4 text-sm text-[#6C31D6] font-medium hover:underline">
              Choose a different plan or length
            </button>
          </div>
        </div>
      )}

      {latest?.status === 'approved' && (
        <p data-testid="approved-note" className="text-sm text-[#15803D]">
          Your payment was approved. Opening your dashboard... <Link to="/dashboard" className="underline">Open it now</Link>
        </p>
      )}
    </SubscribeShell>
  )
}

export default WaitingPage
