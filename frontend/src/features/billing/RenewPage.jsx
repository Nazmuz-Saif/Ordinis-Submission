import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CreditCard } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getPaymentInstructions, getQuote, getSubscription } from '../../services/billingService'
import { MAX_MONTHS, MIN_MONTHS, MONTH_CHOICES, validMonths } from '../../utils/subscription'
import { readError } from '../../utils/apiError'
import EmptyState from '../../components/common/EmptyState'
import PaymentForm from '../../components/billing/PaymentForm'
import { Notice, PageHeader } from '../admin/shared'
import { formatMoney } from '../payroll/payslipFormat'
import { formatDate, monthsText } from '../subscribe/subscribeFormat'

function Line({ label, value, testId }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm">
      <span className="text-[#71717A]">{label}</span>
      <span data-testid={testId} className="text-[#14142B] font-medium text-right">{value}</span>
    </div>
  )
}

// Months picker for an early renewal when there is no invoice yet (more than 7 days before the end).
function EarlyRenewal({ planName, instructions, onSubmitted }) {
  const [preset, setPreset] = useState(12)
  const [custom, setCustom] = useState('')
  const [result, setResult] = useState(null)       // { key, quote } or { key, error }
  const months = preset ?? Number(custom)
  const ok = validMonths(months)
  const key = `${planName}|${months}`
  const fresh = result?.key === key ? result : null

  useEffect(() => {
    if (!ok) return undefined
    let stale = false
    const timer = setTimeout(() => {
      getQuote(planName, months)
        .then((quote) => !stale && setResult({ key, quote }))
        .catch((err) => !stale && setResult({ key, error: readError(err).message }))
    }, 200)
    return () => {
      stale = true
      clearTimeout(timer)
    }
  }, [planName, months, ok, key])

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium text-[#14142B] mb-2">Renew for how long?</p>
        <div className="flex flex-wrap items-center gap-2">
          {MONTH_CHOICES.map((n) => (
            <button
              key={n} type="button" data-testid={`renew-months-${n}`} onClick={() => { setPreset(n); setCustom('') }}
              className={`rounded-lg border px-4 py-2 text-sm font-medium transition ${preset === n ? 'border-[#6C31D6] bg-[#EDE9FE] text-[#6C31D6]' : 'border-[#EEEEF2] bg-white text-[#14142B] hover:border-[#A78BFA]'}`}
            >
              {monthsText(n)}
            </button>
          ))}
          <label className="flex items-center gap-2 text-sm text-[#71717A] ml-2">
            or
            <input
              type="number" min={MIN_MONTHS} max={MAX_MONTHS} step="1" data-testid="renew-months-custom" aria-label="Custom number of months"
              value={custom} onChange={(e) => { setCustom(e.target.value); setPreset(null) }} placeholder="1 to 36"
              className="w-24 border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6]"
            />
            months
          </label>
        </div>
        {!ok && <p className="text-xs text-[#DC2626] mt-2">Enter a whole number of months from {MIN_MONTHS} to {MAX_MONTHS}.</p>}
      </div>
      {fresh?.error && <p role="alert" data-testid="renew-quote-error" className="text-sm text-[#B91C1C]">{fresh.error}</p>}
      {fresh?.quote && (
        <>
          <div className="bg-[#F1EEFB] rounded-lg px-4 py-3 text-sm text-[#14142B]" data-testid="renew-quote">
            <p>{monthsText(fresh.quote.months)} of {fresh.quote.plan.name}: <strong data-testid="renew-quote-total">{formatMoney(fresh.quote.amount, fresh.quote.currency)}</strong></p>
            {Number(fresh.quote.discount) > 0 && <p className="text-[#15803D]">You save {formatMoney(fresh.quote.discount, fresh.quote.currency)}</p>}
            <p className="text-xs text-[#71717A] mt-1">From {formatDate(fresh.quote.period_start)} to {formatDate(fresh.quote.period_end)} once approved.</p>
          </div>
          <PaymentForm key={fresh.quote.months} quote={fresh.quote} instructions={instructions} onSubmitted={onSubmitted} onAlreadyPending={onSubmitted} />
        </>
      )}
    </div>
  )
}

function RenewPage() {
  const { hasPermission } = useAuth()
  const navigate = useNavigate()
  const allowed = hasPermission('manage_billing')
  const [data, setData] = useState(null)
  const [instructions, setInstructions] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!allowed) return
    Promise.all([getSubscription(), getPaymentInstructions()])
      .then(([subscription, info]) => {
        setData(subscription)
        setInstructions(info)
      })
      .catch((err) => setError(readError(err, 'Could not load the renewal.').message))
  }, [allowed])

  if (!allowed) {
    return <EmptyState icon={CreditCard} title="You do not have access to this page" description="Paying for the plan needs the Manage Billing permission." />
  }
  const done = () => navigate('/settings/billing')
  const invoice = data?.renewal_invoice

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader title="Renew your plan" subtitle="Pay outside Ordinis, then send the details. The platform team approves the payment and your plan is extended from its end date, so no days are lost." />
      <Link to="/settings/billing" className="text-sm text-[#6C31D6] font-medium hover:underline">Back to Billing</Link>
      {error && <Notice>{error}</Notice>}
      {!data && !error && <div className="skeleton h-64 rounded-xl" />}

      {data?.pending_payment && (
        <div data-testid="renew-pending" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
          <p className="text-base font-semibold text-[#14142B]">A payment is waiting for approval</p>
          <p className="text-sm text-[#71717A] mt-1">
            {formatMoney(data.pending_payment.amount, data.pending_payment.currency)} by {data.pending_payment.method_label}, transaction {data.pending_payment.transaction_id}.
            You can pay again after the platform team decides.
          </p>
        </div>
      )}

      {data && !data.pending_payment && invoice && (
        <div className="grid gap-6 md:grid-cols-3">
          <div data-testid="renew-invoice" className="md:col-span-1 bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5 h-fit">
            <p className="text-sm text-[#71717A]">Invoice to pay</p>
            <p data-testid="renew-invoice-number" className="text-lg font-bold text-[#14142B]">{invoice.number}</p>
            <p data-testid="renew-invoice-amount" className="text-2xl font-bold text-[#14142B] mt-2">{formatMoney(invoice.amount, invoice.currency)}</p>
            <div className="mt-3 border-t border-[#EEEEF2] pt-2">
              <Line label="Plan" value={invoice.plan_name} />
              <Line label="Length" value={monthsText(invoice.months)} testId="renew-invoice-months" />
              <Line label="Period" value={`${formatDate(invoice.period_start)} to ${formatDate(invoice.period_end)}`} />
              <Line label="Due" value={formatDate(invoice.due_on)} />
            </div>
            <Link to={`/settings/billing/invoices/${invoice.id}`} className="inline-block mt-2 text-sm text-[#6C31D6] font-medium hover:underline">Open the invoice</Link>
          </div>
          <div className="md:col-span-2 bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
            <PaymentForm
              invoiceId={invoice.id}
              quote={{ plan: { name: invoice.plan_name }, months: invoice.months, amount: invoice.amount, currency: invoice.currency }}
              instructions={instructions} submitLabel="Pay this invoice" onSubmitted={done} onAlreadyPending={done}
            />
          </div>
        </div>
      )}

      {data && !data.pending_payment && !invoice && (
        <div data-testid="renew-early" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
          <p className="text-sm text-[#71717A] mb-4">
            Your renewal invoice is issued 7 days before the end. You can also renew early: the new time is added after your current end date.
          </p>
          <EarlyRenewal planName={data.plan.name} instructions={instructions} onSubmitted={done} />
        </div>
      )}
    </div>
  )
}

export default RenewPage
