import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CreditCard } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getInvoicesPage, getSubscription } from '../../services/billingService'
import EmptyState from '../../components/common/EmptyState'
import StatusPill from '../../components/common/StatusPill'
import { DataTable, Notice, PageHeader } from '../admin/shared'
import { usePagedList } from '../admin/usePagedList'
import { formatMoney } from '../payroll/payslipFormat'
import { formatDate, monthsText } from '../subscribe/subscribeFormat'
import TimelineCard from './TimelineCard'

const STATUS = { paid: 'success', open: 'warning', void: 'neutral' }

function seatsText(usage) {
  return usage.unlimited ? `${usage.employees} employees (no limit)` : `${usage.employees} of ${usage.limit} employees`
}

function BillingPage() {
  const { hasPermission } = useAuth()
  const allowed = hasPermission('view_billing')
  const [subscription, setSubscription] = useState(null)
  const [error, setError] = useState('')
  const list = usePagedList(getInvoicesPage)

  const waiting = Boolean(subscription?.pending_payment)

  useEffect(() => {
    if (!allowed) return undefined
    let active = true
    const load = () =>
      getSubscription()
        .then((data) => active && setSubscription(data))
        .catch(() => active && setError('Could not load the plan.'))
    load()
    // while a payment waits for approval the page checks again, so the end date moves by itself
    const timer = waiting ? setInterval(load, 10000) : null
    return () => {
      active = false
      if (timer) clearInterval(timer)
    }
  }, [allowed, waiting])

  if (!allowed) {
    return <EmptyState icon={CreditCard} title="You do not have access to this page" description="Seeing the plan and invoices needs the View Billing permission." />
  }

  const usage = subscription?.usage
  const barColor = usage?.is_full ? 'bg-[#DC2626]' : usage?.percent >= 80 ? 'bg-[#F59E0B]' : 'bg-[#6C31D6]'

  const columns = [
    {
      key: 'number', label: 'Invoice',
      render: (i) => (
        <Link to={`/settings/billing/invoices/${i.id}`} data-testid="invoice-open" className="text-[#6C31D6] hover:underline">
          <span data-testid="invoice-number" className="font-medium">{i.number}</span>
        </Link>
      ),
    },
    { key: 'period', label: 'Period', render: (i) => `${formatDate(i.period_start)} to ${formatDate(i.period_end)}` },
    { key: 'plan', label: 'Plan', render: (i) => `${i.plan_name}, ${monthsText(i.months)}` },
    { key: 'amount', label: 'Amount', render: (i) => <span className="font-semibold">{formatMoney(i.amount, i.currency)}</span> },
    { key: 'due', label: 'Due', render: (i) => formatDate(i.due_on) },
    { key: 'status', label: 'Status', render: (i) => <StatusPill status={STATUS[i.status] || 'neutral'} label={i.status_label} /> },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title="Billing" subtitle="Your plan, how many employee seats you use, and your invoices." />
      {error && <Notice>{error}</Notice>}

      {subscription?.pending_payment && (
        <div data-testid="renewal-pending-banner" className="p-3 border border-amber-200 bg-amber-50 text-amber-800 rounded-lg text-sm">
          Your payment of {formatMoney(subscription.pending_payment.amount, subscription.pending_payment.currency)} ({subscription.pending_payment.method_label},
          transaction {subscription.pending_payment.transaction_id}) is waiting for approval. Your plan is extended as soon as it is approved.
        </div>
      )}

      {subscription?.timeline && (
        <TimelineCard
          timeline={subscription.timeline} planName={subscription.plan.name}
          canPay={hasPermission('manage_billing')} pending={waiting}
        />
      )}

      {subscription && (
        <div className="grid gap-4 md:grid-cols-2">
          <div data-testid="billing-plan-card" className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-5">
            <p className="text-sm text-[#71717A]">Current plan</p>
            <p data-testid="billing-plan-name" className="text-2xl font-bold text-[#14142B] mt-1">{subscription.plan.name}</p>
            <p data-testid="billing-plan-price" className="text-sm text-[#14142B] mt-2">
              {formatMoney(subscription.plan.price_monthly, subscription.plan.currency)} per month
            </p>
            <p data-testid="billing-plan-limit" className="text-sm text-[#71717A] mt-1">
              {subscription.plan.unlimited ? 'No employee limit' : `Up to ${subscription.plan.max_employees} employees`}
            </p>
            {subscription.next_plan && (
              <p data-testid="billing-next-plan" className="text-sm text-[#14142B] mt-3 rounded-lg bg-[#F1EEFB] px-3 py-2">
                {subscription.next_plan_from
                  ? `Changes to ${subscription.next_plan.name} on ${formatDate(subscription.next_plan_from)}.`
                  : `Changes to ${subscription.next_plan.name} at your next renewal.`}
              </p>
            )}
            {hasPermission('manage_billing') && (
              <Link to="/settings/billing/change-plan" data-testid="change-plan-link" className="inline-block mt-3 text-sm text-[#6C31D6] font-medium hover:underline">
                Change plan
              </Link>
            )}
          </div>

          <div data-testid="billing-usage-card" className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-5">
            <p className="text-sm text-[#71717A]">Employee seats</p>
            <p data-testid="billing-usage-text" className="text-2xl font-bold text-[#14142B] mt-1">{seatsText(usage)}</p>
            {!usage.unlimited && (
              <>
                <div className="mt-3 h-2.5 rounded-full bg-[#EEEEF2] overflow-hidden" role="progressbar" aria-valuenow={usage.percent} aria-valuemin={0} aria-valuemax={100}>
                  <div data-testid="billing-usage-bar" className={`h-full rounded-full transition-all duration-300 ${barColor}`} style={{ width: `${usage.percent}%` }} />
                </div>
                <p data-testid="billing-usage-note" className="text-sm mt-2 text-[#14142B]">
                  {usage.is_full ? (
                    <>
                      Your plan is full.{' '}
                      {hasPermission('manage_billing')
                        ? <Link to="/settings/billing/change-plan" data-testid="upgrade-link" className="text-[#6C31D6] font-medium hover:underline">Upgrade your plan</Link>
                        : 'Upgrade your plan'}{' '}
                      to add more employees.
                    </>
                  ) : `${usage.remaining} seat${usage.remaining === 1 ? '' : 's'} left.`}
                </p>
              </>
            )}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-base font-semibold text-[#14142B] mb-3">Invoices</h2>
        {list.error && <Notice>{list.error}</Notice>}
        <DataTable
          testId="billing-invoices" rowTestId="invoice-row" columns={columns} rows={list.data?.items ?? []}
          list={list} page={list.page} onPage={list.setPage}
          emptyTitle="No invoices yet" emptyText="Invoices appear here when a payment is approved or a renewal is due."
        />
      </div>
    </div>
  )
}

export default BillingPage
