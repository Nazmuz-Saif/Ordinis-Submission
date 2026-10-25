import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, Building2, CalendarClock, CheckCircle2, CreditCard, LifeBuoy, Lock, PauseCircle, ShieldCheck, TrendingUp, Wallet } from 'lucide-react'
import MetricCard from '../../components/common/MetricCard'
import ChartCard from '../../components/common/ChartCard'
import { BarChartBox, DonutChartBox } from '../dashboard/charts'
import { getSummary } from '../../services/adminService'
import { formatMoney } from '../payroll/payslipFormat'
import { Notice, PageHeader } from './shared'

// What needs the Platform Owner, in the order of urgency. `text(count)` is the sentence on the row.
const ATTENTION = {
  pending_payments: { path: '/admin/payments', text: (n) => `${n} ${n === 1 ? 'payment' : 'payments'} waiting for your approval`, icon: CreditCard },
  subscriptions_ending: { path: '/admin/subscriptions', text: (n) => `${n} ${n === 1 ? 'subscription ends' : 'subscriptions end'} in 7 days or less`, icon: CalendarClock },
  open_tickets: { path: '/admin/tickets', text: (n) => `${n} open support ${n === 1 ? 'ticket' : 'tickets'}`, icon: LifeBuoy },
  pending_access_requests: { path: '/admin/access-requests', text: (n) => `${n} access ${n === 1 ? 'request' : 'requests'} waiting for a company to answer`, icon: ShieldCheck },
}

function monthName(iso) {
  const [year, month] = iso.split('-').map(Number)
  return new Date(year, month - 1, 1).toLocaleString('en-US', { month: 'short' })
}

function AdminDashboardPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getSummary()
      .then((res) => { if (!cancelled) setData(res) })
      .catch(() => { if (!cancelled) setError('Could not load the platform summary.') })
    return () => { cancelled = true }
  }, [])

  if (error) return <div className="space-y-6"><PageHeader title="Dashboard" /><Notice>{error}</Notice></div>
  const loading = !data
  const c = data?.companies
  const money = (value) => formatMoney(value, data?.revenue.currency)
  const attention = (data?.attention || []).filter((item) => item.count > 0)

  const months = (data?.revenue_by_month || []).map((m) => ({ name: monthName(m.month), value: Number(m.revenue) }))
  const states = c
    ? [{ name: 'Active', value: c.active }, { name: 'Restricted', value: c.restricted }, { name: 'Suspended', value: c.suspended }].filter((s) => s.value > 0)
    : []

  return (
    <div className="space-y-8">
      <PageHeader title="Dashboard" subtitle="The health of the platform at a glance." />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard loading={loading} label="Companies" value={c?.total} icon={Building2} />
        <MetricCard loading={loading} label="Active" value={c?.active} icon={CheckCircle2} />
        <MetricCard loading={loading} label="Restricted" value={c?.restricted} icon={Lock} delta={c?.restricted ? 'Waiting for payment or expired' : undefined} deltaTone="negative" />
        <MetricCard loading={loading} label="Suspended" value={c?.suspended} icon={PauseCircle} />
        <MetricCard loading={loading} label="Revenue this month" value={data && money(data.revenue.this_month)} icon={TrendingUp} />
        <MetricCard loading={loading} label="Revenue all time" value={data && money(data.revenue.all_time)} icon={Wallet} />
        <MetricCard loading={loading} label="Due" value={data && money(data.due.amount)} icon={AlertCircle} delta={data && data.due.count ? `${data.due.count} open ${data.due.count === 1 ? 'invoice' : 'invoices'}` : undefined} deltaTone="negative" />
        <MetricCard loading={loading} label="Ending in 7 days" value={data?.subscriptions_ending} icon={CalendarClock} />
        <MetricCard loading={loading} label="Pending payments" value={data?.pending_payments} icon={CreditCard} />
        <MetricCard loading={loading} label="Open tickets" value={data?.open_tickets} icon={LifeBuoy} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ChartCard title="Revenue per month" subtitle="Paid invoices, last 6 months" loading={loading} empty={data && months.every((m) => m.value === 0)} emptyText="No revenue in the last 6 months.">
            <BarChartBox data={months} valueLabel="Revenue" formatValue={money} />
          </ChartCard>
        </div>
        <ChartCard title="Companies by state" loading={loading} empty={data && states.length === 0} emptyText="No companies yet.">
          <DonutChartBox data={states} />
        </ChartCard>
      </div>

      <section data-testid="attention">
        <h2 className="text-base font-semibold text-[#14142B] mb-3">Needs attention</h2>
        {data && attention.length === 0 && (
          <p data-testid="attention-empty" className="text-sm text-[#71717A] bg-white rounded-xl border border-[#EEEEF2] px-4 py-5">Nothing needs your attention right now.</p>
        )}
        {attention.length > 0 && (
          <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm divide-y divide-[#EEEEF2]">
            {attention.map((item) => {
              const spec = ATTENTION[item.key]
              const Icon = spec.icon
              return (
                <Link
                  key={item.key} to={spec.path} data-testid={`attention-${item.key}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-[#FAFAFA] transition-colors"
                >
                  <Icon size={18} className="text-[#6C31D6] shrink-0" aria-hidden="true" />
                  <span className="flex-1 text-sm text-[#14142B]">{spec.text(item.count)}</span>
                  <span className="rounded-full bg-[#EDE9FE] text-[#6C31D6] text-xs font-medium px-2 py-0.5">{item.count}</span>
                </Link>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}

export default AdminDashboardPage
