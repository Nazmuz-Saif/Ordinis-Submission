import { useEffect, useState } from 'react'
import { CreditCard } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getInvoicesPage, getSubscription } from '../../services/billingService'
import EmptyState from '../../components/common/EmptyState'
import StatusPill from '../../components/common/StatusPill'
import { DataTable, Notice, PageHeader } from '../admin/shared'
import { usePagedList } from '../admin/usePagedList'
import { formatMoney } from '../payroll/payslipFormat'

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

  useEffect(() => {
    if (!allowed) return
    getSubscription().then(setSubscription).catch(() => setError('Could not load the plan.'))
  }, [allowed])

  if (!allowed) {
    return <EmptyState icon={CreditCard} title="You do not have access to this page" description="Seeing the plan and invoices needs the View Billing permission." />
  }

  const usage = subscription?.usage
  const barColor = usage?.is_full ? 'bg-[#DC2626]' : usage?.percent >= 80 ? 'bg-[#F59E0B]' : 'bg-[#6C31D6]'

  const columns = [
    { key: 'number', label: 'Invoice', render: (i) => <span data-testid="invoice-number" className="font-medium">{i.number}</span> },
    { key: 'period', label: 'Period', render: (i) => `${i.period_start} to ${i.period_end}` },
    { key: 'plan', label: 'Plan', render: (i) => i.plan_name },
    { key: 'amount', label: 'Amount', render: (i) => <span className="font-semibold">{formatMoney(i.amount, i.currency)}</span> },
    { key: 'due', label: 'Due', render: (i) => i.due_on },
    { key: 'status', label: 'Status', render: (i) => <StatusPill status={STATUS[i.status] || 'neutral'} label={i.status_label} /> },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title="Billing" subtitle="Your plan, how many employee seats you use, and your invoices." />
      {error && <Notice>{error}</Notice>}

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
            <p className="text-xs text-[#71717A] mt-3">To change your plan, contact the Ordinis team.</p>
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
                  {usage.is_full ? 'Your plan is full. Upgrade your plan to add more employees.' : `${usage.remaining} seat${usage.remaining === 1 ? '' : 's'} left.`}
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
          emptyTitle="No invoices yet" emptyText="Monthly invoices appear here."
        />
      </div>
    </div>
  )
}

export default BillingPage
