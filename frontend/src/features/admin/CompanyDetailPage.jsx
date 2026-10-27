import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, KeyRound, Power, PowerOff } from 'lucide-react'
import { getCompany } from '../../services/adminService'
import StatusPill from '../../components/common/StatusPill'
import { formatMoney } from '../payroll/payslipFormat'
import { formatDate as formatDay } from '../subscribe/subscribeFormat'
import { Notice } from './shared'
import { formatDate } from './format'
import { daysLeftCell } from './subscriptionFormat'
import CompanyStatusDialog from './CompanyStatusDialog'
import RequestAccessDialog from './RequestAccessDialog'

const ACTION_LABELS = {
  suspend: 'Suspended', activate: 'Activated', resolve_ticket: 'Ticket resolved', reopen_ticket: 'Ticket reopened',
  approve_payment: 'Payment approved', reject_payment: 'Payment rejected',
}
const STATE_LABELS = { active: 'Active', grace: 'Grace period', expired: 'Expired', pending_payment: 'Waiting for payment', cancelled: 'Cancelled' }
const STATE_TONES = { active: 'success', grace: 'warning', expired: 'failed', pending_payment: 'warning', cancelled: 'neutral' }

function Card({ title, testId, children }) {
  return (
    <section data-testid={testId} className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
      <h2 className="text-sm font-semibold text-[#14142B] mb-3">{title}</h2>
      <dl className="space-y-1.5 text-sm">{children}</dl>
    </section>
  )
}

function Line({ label, value, testId }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-[#71717A]">{label}</dt>
      <dd data-testid={testId} className="text-[#14142B] font-medium text-right break-words">{value ?? '-'}</dd>
    </div>
  )
}

function actionText(row) {
  return ACTION_LABELS[row.action] || row.action.replaceAll('_', ' ')
}

function CompanyDetailPage() {
  const { id } = useParams()
  const [company, setCompany] = useState(null)
  const [error, setError] = useState('')
  const [dialog, setDialog] = useState(null)            // 'suspend' | 'activate' | 'access'
  const [message, setMessage] = useState('')

  const load = useCallback(
    () => getCompany(id).then(setCompany).catch((err) => setError(err.response?.status === 404 ? 'This company was not found.' : 'Could not load the company.')),
    [id],
  )
  useEffect(() => { load() }, [load])

  const back = (
    <Link to="/admin/companies" className="inline-flex items-center gap-1 text-sm text-[#71717A] hover:text-[#6C31D6]">
      <ArrowLeft size={14} /> Companies
    </Link>
  )
  if (error) return <div className="space-y-4">{back}<Notice testId="company-error">{error}</Notice></div>
  if (!company) return <div className="space-y-4">{back}<div className="skeleton h-64 rounded-xl" /></div>

  const sub = company.subscription
  const left = sub ? daysLeftCell({ days_left: sub.days_left, status: sub.status }) : null
  const size = company.size
  const last = company.last_status_action
  const owner = company.owner

  return (
    <div className="space-y-6">
      {back}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 data-testid="company-name" className="text-xl font-bold text-[#14142B]">{company.name}</h1>
            <span data-testid="company-status"><StatusPill status={company.is_active ? 'success' : 'failed'} label={company.is_active ? 'Active' : 'Suspended'} /></span>
          </div>
          <p className="text-sm text-[#71717A] mt-1">
            <span data-testid="company-subdomain">{company.subdomain}</span>
            {company.industry ? ` · ${company.industry}` : ''} · Registered {formatDay(company.registered_on.slice(0, 10))}
          </p>
          {last && (
            <p data-testid="company-last-status" className="text-sm text-[#14142B] mt-2">
              {last.action === 'suspend' ? 'Suspended' : 'Activated'} on {formatDate(last.created_at)} by {last.actor_name}
              {last.note ? <>: <span data-testid="company-last-note">{last.note}</span></> : '.'}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button" data-testid="request-access-btn" onClick={() => setDialog('access')}
            className="inline-flex items-center gap-1.5 border border-[#EEEEF2] hover:border-[#A78BFA] rounded-lg px-3 py-2 text-sm font-medium text-[#14142B]"
          >
            <KeyRound size={15} /> Request access
          </button>
          {company.is_active ? (
            <button
              type="button" data-testid="suspend-btn" onClick={() => setDialog('suspend')}
              className="inline-flex items-center gap-1.5 border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-2 text-sm font-medium"
            >
              <PowerOff size={15} /> Suspend
            </button>
          ) : (
            <button
              type="button" data-testid="activate-btn" onClick={() => setDialog('activate')}
              className="inline-flex items-center gap-1.5 bg-[#16A34A] hover:bg-[#15803D] text-white rounded-lg px-3 py-2 text-sm font-medium"
            >
              <Power size={15} /> Activate
            </button>
          )}
        </div>
      </div>

      {message && <Notice kind="success" testId="company-message">{message}</Notice>}
      <p className="text-xs text-[#71717A]">
        This page shows contacts and counts only. Employee names, tasks, attendance and salaries stay private; Request access asks the company's CEO to open them for a limited time.
      </p>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card title="Owner" testId="company-owner">
          <Line label="Name" value={owner?.full_name} testId="owner-name" />
          <Line label="Email" value={owner?.email} testId="owner-email" />
          <Line label="Phone" value={owner?.phone || '-'} testId="owner-phone" />
        </Card>

        <Card title="Plan and subscription" testId="company-plan">
          {sub ? (
            <>
              <Line label="Plan" value={`${sub.plan.name} (${formatMoney(sub.plan.price_monthly, sub.plan.currency)} / month)`} testId="plan-name" />
              <Line label="State" value={<StatusPill status={STATE_TONES[sub.status] || 'neutral'} label={STATE_LABELS[sub.status] || sub.status} />} testId="plan-state" />
              <Line label="Started" value={formatDay(sub.started_on)} testId="plan-started" />
              <Line label="Ends" value={formatDay(sub.period_end)} testId="plan-end" />
              <Line label="Days left" value={left.text} testId="plan-days-left" />
              {sub.next_plan && <Line label="Next plan" value={sub.next_plan} testId="plan-next" />}
            </>
          ) : <p className="text-[#71717A]">No subscription yet.</p>}
        </Card>

        <Card title="Size" testId="company-size">
          <Line label="Employees" value={size.unlimited ? `${size.employees} (no limit)` : `${size.employees} of ${size.limit}`} testId="size-text" />
          {!size.unlimited && (
            <div className="h-2 rounded-full bg-[#EEEEF2] overflow-hidden" role="progressbar" aria-valuenow={size.percent} aria-valuemin={0} aria-valuemax={100}>
              <div className={`h-full rounded-full ${size.is_full ? 'bg-[#DC2626]' : 'bg-[#6C31D6]'}`} style={{ width: `${size.percent}%` }} />
            </div>
          )}
          {size.is_full && <p className="text-xs text-[#B91C1C]">The plan is full.</p>}
        </Card>

        <Card title="Invoices" testId="company-invoices">
          <Line label="Total" value={company.invoices.total} testId="invoices-total" />
          <Line label="Open" value={`${company.invoices.open} (${formatMoney(company.invoices.open_amount, sub?.plan.currency || 'BDT')})`} testId="invoices-open" />
          <Line label="Paid" value={`${company.invoices.paid} (${formatMoney(company.invoices.paid_amount, sub?.plan.currency || 'BDT')})`} testId="invoices-paid" />
        </Card>

        <Card title="Payments" testId="company-payments">
          <Line label="Total" value={company.payments.total} testId="payments-total" />
          <Line label="Waiting for approval" value={company.payments.pending} testId="payments-pending" />
          <Line label="Approved" value={`${company.payments.approved} (${formatMoney(company.payments.approved_amount, sub?.plan.currency || 'BDT')})`} testId="payments-approved" />
          <Line label="Rejected" value={company.payments.rejected} testId="payments-rejected" />
          <Line label="Last approved" value={company.payments.last_approved_at ? formatDate(company.payments.last_approved_at) : 'Never'} testId="payments-last" />
        </Card>

        <Card title="Support" testId="company-support">
          <Line label="Open tickets" value={`${company.tickets.open} of ${company.tickets.total}`} testId="tickets-open" />
          <Line label="Access requests waiting" value={company.access_requests.pending} testId="requests-pending" />
          <Line label="Access running now" value={company.access_requests.active} testId="requests-active" />
        </Card>
      </div>

      <div>
        <h2 className="text-base font-semibold text-[#14142B] mb-3">Recent platform actions</h2>
        {company.recent_actions.length === 0 ? (
          <p data-testid="actions-empty" className="text-sm text-[#71717A]">Nothing has been done to this company yet.</p>
        ) : (
          <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm overflow-x-auto">
            <table data-testid="company-actions" className="w-full text-sm">
              <thead>
                <tr className="text-left text-[#71717A] border-b border-[#EEEEF2]">
                  <th className="px-4 py-3 font-medium">Action</th>
                  <th className="px-4 py-3 font-medium">Note</th>
                  <th className="px-4 py-3 font-medium">By</th>
                  <th className="px-4 py-3 font-medium">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EEEEF2]">
                {company.recent_actions.map((row) => (
                  <tr key={row.id} data-testid="company-action-row" className="text-[#14142B]">
                    <td className="px-4 py-3 whitespace-nowrap">{actionText(row)}</td>
                    <td className="px-4 py-3">{row.note || <span className="text-[#71717A]">-</span>}</td>
                    <td className="px-4 py-3 whitespace-nowrap">{row.actor_name}</td>
                    <td className="px-4 py-3 text-[#71717A] whitespace-nowrap">{formatDate(row.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {(dialog === 'suspend' || dialog === 'activate') && (
        <CompanyStatusDialog
          company={company} kind={dialog} onCancel={() => setDialog(null)}
          onDone={(kind) => { setMessage(kind === 'suspend' ? `${company.name} is suspended.` : `${company.name} is active again.`); setDialog(null); load() }}
        />
      )}
      {dialog === 'access' && (
        <RequestAccessDialog
          company={company} onCancel={() => setDialog(null)}
          onDone={() => { setMessage(`Access request sent to ${company.name}. Its CEO decides.`); setDialog(null); load() }}
        />
      )}
    </div>
  )
}

export default CompanyDetailPage
