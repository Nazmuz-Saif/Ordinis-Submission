import { useCallback, useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { approvePayment, getPaymentsPage, rejectPayment } from '../../services/adminService'
import StatusPill from '../../components/common/StatusPill'
import { PAYMENTS_CHANGED } from '../../components/layout/usePendingPayments'
import { formatMoney } from '../payroll/payslipFormat'
import { formatDate as formatDay, monthsText } from '../subscribe/subscribeFormat'
import { ConfirmDialog, DataTable, Notice, PageHeader } from './shared'
import { formatDate } from './format'
import { usePagedList } from './usePagedList'

const STATUS_TABS = [
  { key: 'pending', label: 'Pending' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
  { key: '', label: 'All' },
]
const METHODS = [
  { key: '', label: 'All methods' },
  { key: 'bkash', label: 'bKash' },
  { key: 'nagad', label: 'Nagad' },
  { key: 'bank', label: 'Bank transfer' },
  { key: 'cash', label: 'Cash' },
]
const inputClass = 'border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] bg-white'

function Field({ label, children, testId }) {
  return (
    <>
      <dt className="text-[#71717A]">{label}</dt>
      <dd data-testid={testId} className="text-[#14142B] font-medium break-words">{children}</dd>
    </>
  )
}

function DetailPanel({ payment, onClose, onApprove, onReject }) {
  return (
    <>
      <div className="fixed inset-0 z-40 bg-[#14142B]/30" onClick={onClose} />
      <aside data-testid="payment-detail" className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-xl border-l border-[#EEEEF2] overflow-y-auto p-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-[#14142B]">Payment from {payment.company_name}</h2>
            <div className="mt-2" data-testid="detail-status"><StatusPill status={payment.status} label={payment.status_label} /></div>
          </div>
          <button type="button" aria-label="Close" data-testid="detail-close" onClick={onClose} className="p-1 rounded-lg hover:bg-[#FAFAFA]"><X size={18} /></button>
        </div>

        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm mt-5">
          <Field label="Company">{payment.company_name} ({payment.company_subdomain})</Field>
          <Field label="Kind" testId="detail-kind">{payment.kind_label}</Field>
          <Field label="Plan" testId="detail-plan">{payment.plan_name} for {monthsText(payment.months)}</Field>
          <Field label="Amount" testId="detail-amount">{formatMoney(payment.amount, payment.currency)}</Field>
          <Field label="Paid with" testId="detail-method">{payment.method_label}</Field>
          <Field label="Payer" testId="detail-payer">{payment.payer_name}</Field>
          <Field label="Number" testId="detail-number">{payment.payer_number}</Field>
          <Field label="Transaction id" testId="detail-transaction">{payment.transaction_id}</Field>
          <Field label="Submitted">{formatDate(payment.created_at)}</Field>
          <Field label="Submitted by">{payment.submitted_by_name || payment.submitted_by_email || '-'}</Field>
        </dl>

        {payment.status === 'approved' && (
          <div data-testid="approved-result" className="mt-6 rounded-lg bg-[#16A34A]/10 text-[#15803D] text-sm px-4 py-3 space-y-1">
            <p className="font-semibold">Approved{payment.reviewed_by_name ? ` by ${payment.reviewed_by_name}` : ''}</p>
            <p data-testid="result-end-date">Plan runs until {formatDay(payment.period_end)}</p>
            <p data-testid="result-invoice">Invoice {payment.invoice_number}</p>
          </div>
        )}
        {payment.status === 'rejected' && (
          <div className="mt-6 rounded-lg bg-[#DC2626]/10 text-[#B91C1C] text-sm px-4 py-3 space-y-1">
            <p className="font-semibold">Rejected{payment.reviewed_by_name ? ` by ${payment.reviewed_by_name}` : ''}</p>
            <p data-testid="detail-rejected-note">{payment.review_note}</p>
          </div>
        )}
        {payment.status === 'pending' && (
          <div className="mt-6 flex gap-2">
            <button type="button" data-testid="approve-btn" onClick={onApprove} className="bg-[#16A34A] hover:bg-[#15803D] text-white rounded-lg px-4 py-2 text-sm font-medium">Approve</button>
            <button type="button" data-testid="reject-btn" onClick={onReject} className="border border-[#DC2626] text-[#B91C1C] hover:bg-[#DC2626]/10 rounded-lg px-4 py-2 text-sm font-medium">Reject</button>
          </div>
        )}
      </aside>
    </>
  )
}

function PaymentsPage() {
  const [status, setStatus] = useState('pending')
  const [method, setMethod] = useState('')
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const [detail, setDetail] = useState(null)
  const [dialog, setDialog] = useState(null)        // 'approve' | 'reject'
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [dialogError, setDialogError] = useState('')
  const [message, setMessage] = useState('')

  // the search box waits for a short pause in typing
  useEffect(() => {
    const timer = setTimeout(() => setQ(search.trim()), 300)
    return () => clearTimeout(timer)
  }, [search])

  const load = useCallback((page) => getPaymentsPage(page, { status, method, q }), [status, method, q])
  const list = usePagedList(load, `${status}|${method}|${q}`)

  function closeDialog() {
    setDialog(null)
    setNote('')
    setDialogError('')
  }

  async function decide() {
    setBusy(true)
    setDialogError('')
    try {
      const res = dialog === 'approve' ? await approvePayment(detail.id) : await rejectPayment(detail.id, note)
      setDetail(res.data)
      setMessage(dialog === 'approve'
        ? `Approved. ${res.data.company_name}'s plan runs until ${formatDay(res.data.period_end)}. Invoice ${res.data.invoice_number}.`
        : `Rejected. ${res.data.company_name} can read your note and send the payment again.`)
      closeDialog()
      list.reload()
      window.dispatchEvent(new Event(PAYMENTS_CHANGED))
    } catch (err) {
      setDialogError(err.response?.data?.error?.message || 'Could not save the decision.')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { key: 'company', label: 'Company', render: (p) => <span className="font-medium whitespace-nowrap">{p.company_name}</span> },
    { key: 'plan', label: 'Plan', render: (p) => <span className="whitespace-nowrap">{p.plan_name}, {monthsText(p.months)}</span> },
    { key: 'amount', label: 'Amount', render: (p) => <span className="whitespace-nowrap font-medium">{formatMoney(p.amount, p.currency)}</span> },
    { key: 'method', label: 'Method', render: (p) => p.method_label },
    { key: 'payer', label: 'Payer', render: (p) => (<><p>{p.payer_name}</p><p className="text-xs text-[#71717A]">{p.payer_number}</p></>) },
    { key: 'txn', label: 'Transaction id', render: (p) => <span className="font-mono text-xs">{p.transaction_id}</span> },
    { key: 'kind', label: 'Kind', render: (p) => p.kind_label },
    { key: 'status', label: 'Status', render: (p) => <StatusPill status={p.status} label={p.status_label} /> },
    { key: 'created', label: 'Submitted', render: (p) => <span className="text-[#71717A] whitespace-nowrap">{formatDate(p.created_at)}</span> },
    {
      key: 'action', label: 'Action', align: 'right',
      render: (p) => (
        <button
          type="button" data-testid="payment-open" onClick={() => setDetail(p)}
          className={p.status === 'pending' ? 'bg-[#6C31D6] hover:bg-[#5B27B8] text-white rounded-lg px-3 py-1.5 text-sm font-medium' : 'border border-[#EEEEF2] text-[#14142B] hover:bg-[#FAFAFA] rounded-lg px-3 py-1.5 text-sm font-medium'}
        >
          {p.status === 'pending' ? 'Review' : 'Open'}
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-5">
      <PageHeader title="Payments" subtitle="Payments companies made outside Ordinis. Check each one, then approve or reject it." />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#EEEEF2]">
        <div className="flex gap-1">
          {STATUS_TABS.map((f) => (
            <button
              key={f.key || 'all'} type="button" data-testid={`filter-${f.key || 'all'}`} onClick={() => setStatus(f.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-150 ${status === f.key ? 'border-[#6C31D6] text-[#6C31D6]' : 'border-transparent text-[#71717A] hover:text-[#14142B]'}`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 pb-2">
          <select aria-label="Method" data-testid="method-filter" value={method} onChange={(e) => setMethod(e.target.value)} className={inputClass}>
            {METHODS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
          <input
            type="search" aria-label="Search payments" data-testid="payments-search" placeholder="Company, payer or transaction id"
            value={search} onChange={(e) => setSearch(e.target.value)} className={`${inputClass} w-64`}
          />
        </div>
      </div>
      {message && <Notice kind="success" testId="payments-message">{message}</Notice>}
      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="payments-table" rowTestId="payment-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage}
        emptyTitle={status === 'pending' ? 'No payments waiting' : 'No payments'} emptyText="Nothing to show for this filter."
      />

      {detail && !dialog && (
        <DetailPanel payment={detail} onClose={() => setDetail(null)} onApprove={() => setDialog('approve')} onReject={() => setDialog('reject')} />
      )}
      {detail && dialog === 'approve' && (
        <ConfirmDialog title="Approve this payment?" confirmLabel="Approve" busy={busy} error={dialogError} onCancel={closeDialog} onConfirm={decide}>
          <p>
            Confirm that you received <strong>{formatMoney(detail.amount, detail.currency)}</strong> from <strong>{detail.company_name}</strong> by{' '}
            {detail.method_label} (transaction <span className="font-mono">{detail.transaction_id}</span>).
          </p>
          <p>Approving starts or extends the {detail.plan_name} plan for {monthsText(detail.months)} and writes a paid invoice.</p>
        </ConfirmDialog>
      )}
      {detail && dialog === 'reject' && (
        <ConfirmDialog title="Reject this payment?" confirmLabel="Reject" danger busy={busy} error={dialogError} onCancel={closeDialog} onConfirm={decide}>
          <p>The company will read your note, so say what is wrong.</p>
          <label htmlFor="reject-note" className="sr-only">Reason</label>
          <textarea
            id="reject-note" data-testid="reject-note" rows={3} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)}
            placeholder="For example: we could not find this transaction."
            className="w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm text-[#14142B] outline-none focus:border-[#6C31D6]"
          />
        </ConfirmDialog>
      )}
    </div>
  )
}

export default PaymentsPage
