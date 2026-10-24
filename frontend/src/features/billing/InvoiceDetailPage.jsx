import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { FileText, Printer } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getInvoice } from '../../services/billingService'
import EmptyState from '../../components/common/EmptyState'
import StatusPill from '../../components/common/StatusPill'
import { formatMoney } from '../payroll/payslipFormat'
import { formatDate, monthsText } from '../subscribe/subscribeFormat'

const STATUS = { paid: 'success', open: 'warning', void: 'neutral' }

function Row({ label, value, testId }) {
  return (
    <div className="grid grid-cols-3 gap-4 py-3 border-b border-[#EEEEF2] last:border-0 text-sm">
      <dt className="text-[#71717A]">{label}</dt>
      <dd data-testid={testId} className="col-span-2 text-[#14142B] font-medium break-words">{value}</dd>
    </div>
  )
}

// One invoice, with a Print button. The menu and top bar are hidden when printing (print:hidden in the layout).
function InvoiceDetailPage() {
  const { id } = useParams()
  const { hasPermission } = useAuth()
  const allowed = hasPermission('view_billing')
  const [state, setState] = useState({ id: null, invoice: null, missing: false })

  useEffect(() => {
    if (!allowed) return undefined
    let active = true
    getInvoice(id)
      .then((invoice) => {
        if (active) setState({ id, invoice, missing: false })
      })
      .catch(() => {
        if (active) setState({ id, invoice: null, missing: true })
      })
    return () => {
      active = false
    }
  }, [id, allowed])

  if (!allowed) {
    return <EmptyState icon={FileText} title="You do not have access to this page" description="Seeing invoices needs the View Billing permission." />
  }
  const current = state.id === id ? state : { invoice: null, missing: false }
  if (current.missing) {
    return (
      <div data-testid="invoice-not-found">
        <EmptyState icon={FileText} title="Invoice not found" description="This invoice does not exist, or it belongs to another company." />
        <p className="text-center mt-4"><Link to="/settings/billing" className="text-sm text-[#6C31D6] font-medium hover:underline">Back to Billing</Link></p>
      </div>
    )
  }
  const invoice = current.invoice
  if (!invoice) return <div className="skeleton h-72 rounded-xl max-w-2xl" />

  const paid = invoice.status === 'paid'
  return (
    <div className="max-w-2xl space-y-5" data-testid="invoice-detail">
      <div className="flex items-start justify-between gap-3 print:hidden">
        <Link to="/settings/billing" data-testid="invoice-back" className="text-sm text-[#6C31D6] font-medium hover:underline">Back to Billing</Link>
        <div className="flex gap-2">
          {invoice.status === 'open' && invoice.kind === 'renewal' && hasPermission('manage_billing') && (
            <Link to="/settings/billing/renew" data-testid="invoice-pay" className="bg-[#6C31D6] text-white rounded-lg px-4 py-2 text-sm font-medium">Pay this invoice</Link>
          )}
          <button type="button" data-testid="invoice-print" onClick={() => window.print()} className="flex items-center gap-2 border border-[#EEEEF2] bg-white hover:bg-[#FAFAFA] rounded-lg px-4 py-2 text-sm font-medium text-[#14142B]">
            <Printer size={16} aria-hidden="true" /> Print
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-6 print:shadow-none print:border-0 print:p-0">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm text-[#71717A]">Invoice</p>
            <h1 data-testid="invoice-detail-number" className="text-2xl font-bold text-[#14142B]">{invoice.number}</h1>
          </div>
          <span data-testid="invoice-detail-status"><StatusPill status={STATUS[invoice.status] || 'neutral'} label={invoice.status_label} /></span>
        </div>
        <p data-testid="invoice-detail-amount" className="text-3xl font-bold text-[#14142B] mt-4">{formatMoney(invoice.amount, invoice.currency)}</p>

        <dl className="mt-5">
          <Row label="Company" value={invoice.company_name} testId="invoice-detail-company" />
          <Row label="Plan" value={invoice.plan_name} testId="invoice-detail-plan" />
          <Row label="Period" value={`${formatDate(invoice.period_start)} to ${formatDate(invoice.period_end)}`} testId="invoice-detail-period" />
          <Row label="Length" value={monthsText(invoice.months)} testId="invoice-detail-months" />
          <Row label="Currency" value={invoice.currency} testId="invoice-detail-currency" />
          <Row label="Issued on" value={formatDate(invoice.issued_on)} testId="invoice-detail-issued" />
          <Row label="Due on" value={formatDate(invoice.due_on)} testId="invoice-detail-due" />
          <Row label="Paid on" value={paid && invoice.paid_on ? formatDate(invoice.paid_on) : 'Not paid yet'} testId="invoice-detail-paid" />
          <Row label="Payment method" value={invoice.payment_method_label || '-'} testId="invoice-detail-method" />
          <Row label="Transaction id" value={invoice.transaction_id || '-'} testId="invoice-detail-transaction" />
        </dl>
      </div>
    </div>
  )
}

export default InvoiceDetailPage
