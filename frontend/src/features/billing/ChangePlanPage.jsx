import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CreditCard } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import {
  cancelDowngrade, getPaymentInstructions, getPlans, getSubscription, getUpgradeQuote, scheduleDowngrade,
} from '../../services/billingService'
import { readError } from '../../utils/apiError'
import EmptyState from '../../components/common/EmptyState'
import PaymentForm from '../../components/billing/PaymentForm'
import { Notice, PageHeader } from '../admin/shared'
import { formatMoney } from '../payroll/payslipFormat'
import { formatDate } from '../subscribe/subscribeFormat'

function limitText(plan) {
  return plan.unlimited ? 'No employee limit' : `Up to ${plan.max_employees} employees`
}

// A plan is "higher" or "lower" by its monthly price, the same rule the server uses.
function relation(plan, current) {
  const a = Number(plan.price_monthly)
  const b = Number(current.price_monthly)
  return a > b ? 'higher' : a < b ? 'lower' : 'current'
}

function ChangePlanPage() {
  const { hasPermission } = useAuth()
  const navigate = useNavigate()
  const allowed = hasPermission('manage_billing')
  const [subscription, setSubscription] = useState(null)
  const [plans, setPlans] = useState([])
  const [instructions, setInstructions] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [chosen, setChosen] = useState('')                 // the higher plan the person is looking at
  const [result, setResult] = useState(null)               // { plan, quote } or { plan, error } for `chosen`
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const [busy, setBusy] = useState(false)

  const reload = useCallback(
    () => getSubscription().then(setSubscription).catch((err) => setLoadError(readError(err, 'Could not load your plan.').message)),
    [],
  )

  useEffect(() => {
    if (!allowed) return
    Promise.all([getSubscription(), getPlans(), getPaymentInstructions()])
      .then(([sub, list, info]) => {
        setSubscription(sub)
        setPlans(list)
        setInstructions(info)
      })
      .catch((err) => setLoadError(readError(err, 'Could not load the plans.').message))
  }, [allowed])

  useEffect(() => {
    if (!chosen) return undefined
    let stale = false
    getUpgradeQuote(chosen)
      .then((quote) => !stale && setResult({ plan: chosen, quote }))
      .catch((err) => !stale && setResult({ plan: chosen, error: readError(err).message }))
    return () => { stale = true }
  }, [chosen])

  if (!allowed) {
    return <EmptyState icon={CreditCard} title="You do not have access to this page" description="Changing the plan needs the Manage Billing permission." />
  }

  const current = subscription?.plan
  const waiting = Boolean(subscription?.pending_payment)
  const view = result?.plan === chosen ? result : null

  async function chooseLower(plan) {
    setActionError('')
    setNotice('')
    setBusy(true)
    try {
      await scheduleDowngrade(plan.name)
      setNotice(`${plan.name} will start at your next renewal. Until then you stay on ${current.name}.`)
      await reload()
    } catch (err) {
      setActionError(readError(err, 'The lower plan could not be scheduled.').message)
    } finally {
      setBusy(false)
    }
  }

  async function cancelLower() {
    setActionError('')
    setNotice('')
    setBusy(true)
    try {
      await cancelDowngrade()
      setNotice(`You stay on ${current.name}.`)
      await reload()
    } catch (err) {
      setActionError(readError(err, 'The lower plan could not be cancelled.').message)
    } finally {
      setBusy(false)
    }
  }

  const done = () => navigate('/settings/billing')

  return (
    <div className="space-y-6 max-w-4xl">
      <PageHeader title="Change plan" subtitle="A higher plan starts as soon as the platform team approves your payment, and you pay only for the days left. A lower plan starts at your next renewal." />
      <Link to="/settings/billing" className="text-sm text-[#6C31D6] font-medium hover:underline">Back to Billing</Link>
      {loadError && <Notice>{loadError}</Notice>}
      {actionError && <Notice>{actionError}</Notice>}
      {notice && <p role="status" data-testid="change-plan-notice" className="rounded-lg bg-[#F1EEFB] text-sm text-[#14142B] px-4 py-3">{notice}</p>}
      {!subscription && !loadError && <div className="skeleton h-64 rounded-xl" />}

      {subscription && (
        <>
          {waiting && (
            <p data-testid="change-plan-pending" className="p-3 border border-amber-200 bg-amber-50 text-amber-800 rounded-lg text-sm">
              A payment of {formatMoney(subscription.pending_payment.amount, subscription.pending_payment.currency)} is waiting for approval.
              You can change the plan after the platform team decides.
            </p>
          )}

          <div className="grid gap-4 md:grid-cols-3" data-testid="change-plan-list">
            {plans.map((plan) => {
              const rel = relation(plan, current)
              const scheduled = subscription.next_plan?.id === plan.id
              return (
                <div
                  key={plan.id} data-testid={`plan-option-${plan.name}`}
                  className={`bg-white rounded-xl border shadow-sm p-5 flex flex-col ${rel === 'current' ? 'border-[#6C31D6]' : 'border-[#EEEEF2]'}`}
                >
                  <p className="text-lg font-bold text-[#14142B]">{plan.name}</p>
                  <p className="text-sm text-[#14142B] mt-1">{formatMoney(plan.price_monthly, plan.currency)} per month</p>
                  <p className="text-sm text-[#71717A] mt-1">{limitText(plan)}</p>
                  <div className="mt-4 flex-1 flex items-end">
                    {rel === 'current' && <span data-testid={`plan-current-${plan.name}`} className="text-sm font-medium text-[#6C31D6]">Your current plan</span>}
                    {rel === 'higher' && (
                      <button
                        type="button" data-testid={`plan-upgrade-${plan.name}`} disabled={waiting}
                        onClick={() => { setResult(null); setChosen(plan.name); setNotice(''); setActionError('') }}
                        className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition"
                      >
                        Upgrade to {plan.name}
                      </button>
                    )}
                    {rel === 'lower' && !scheduled && (
                      <button
                        type="button" data-testid={`plan-lower-${plan.name}`} disabled={busy}
                        onClick={() => chooseLower(plan)}
                        className="border border-[#EEEEF2] hover:border-[#A78BFA] disabled:opacity-50 text-[#14142B] rounded-lg px-4 py-2 text-sm font-medium transition"
                      >
                        Switch at next renewal
                      </button>
                    )}
                    {rel === 'lower' && scheduled && (
                      <div className="space-y-2">
                        <p data-testid={`plan-scheduled-${plan.name}`} className="text-sm font-medium text-[#14142B]">
                          {subscription.next_plan_from ? `Starts on ${formatDate(subscription.next_plan_from)}` : 'Starts at your next renewal'}
                        </p>
                        {!subscription.next_plan_from && (
                          <button type="button" data-testid="plan-cancel-lower" disabled={busy} onClick={cancelLower} className="text-sm text-[#6C31D6] font-medium hover:underline">
                            Stay on {current.name}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {chosen && !waiting && !view && <div className="skeleton h-32 rounded-xl" />}
          {view?.error && <Notice>{view.error}</Notice>}
          {view?.quote && (
            <div className="grid gap-6 md:grid-cols-3">
              <div data-testid="upgrade-quote" className="md:col-span-1 bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5 h-fit">
                <p className="text-sm text-[#71717A]">Extra amount to pay now</p>
                <p data-testid="upgrade-amount" className="text-2xl font-bold text-[#14142B] mt-1">{formatMoney(view.quote.amount, view.quote.currency)}</p>
                <p data-testid="upgrade-formula" className="text-xs text-[#71717A] mt-2">
                  ({formatMoney(view.quote.monthly_price, view.quote.currency)} − {formatMoney(view.quote.current_monthly_price, view.quote.currency)}) × {view.quote.days_left} days left ÷ {view.quote.days_in_month}
                </p>
                <div className="mt-3 border-t border-[#EEEEF2] pt-2 text-sm space-y-1">
                  <p className="flex justify-between gap-3"><span className="text-[#71717A]">From</span><span>{view.quote.current_plan.name}</span></p>
                  <p className="flex justify-between gap-3"><span className="text-[#71717A]">To</span><span data-testid="upgrade-target">{view.quote.plan.name}</span></p>
                  <p className="flex justify-between gap-3"><span className="text-[#71717A]">Days left</span><span data-testid="upgrade-days-left">{view.quote.days_left}</span></p>
                  <p className="flex justify-between gap-3"><span className="text-[#71717A]">Ends on</span><span data-testid="upgrade-end-date">{formatDate(view.quote.period_end)}</span></p>
                </div>
                <p className="text-xs text-[#71717A] mt-3">Your end date does not change.</p>
              </div>
              <div className="md:col-span-2 bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
                <PaymentForm
                  key={view.quote.plan.name} kind="upgrade" quote={view.quote} instructions={instructions}
                  submitLabel="Send upgrade payment" onSubmitted={done} onAlreadyPending={done}
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default ChangePlanPage
