import { useCallback, useEffect, useState } from 'react'
import { CalendarCheck } from 'lucide-react'
import {
  applyLeave, cancelLeave, getLeaveBalance, getLeaveRequestsPage, getLeaveTypes,
} from '../../services/leaveService'
import StatusPill from '../../components/common/StatusPill'
import ApprovalProgress from './ApprovalProgress'
import { ConfirmDialog, DataTable, Notice, PageHeader } from '../admin/shared'
import { usePagedList } from '../admin/usePagedList'
import { STATUS, daysBetween, errorText, plural } from './leaveFormat'

const input = 'mt-1 w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm bg-white outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15'
const FILTERS = [
  { key: '', label: 'All' }, { key: 'pending', label: 'Pending' }, { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' }, { key: 'cancelled', label: 'Cancelled' },
]
const EMPTY = { leave_type: '', start_date: '', end_date: '', reason: '' }

function BalanceCards({ balance }) {
  if (!balance) return <div className="skeleton h-24 w-full rounded-xl" />
  if (balance.length === 0) return <Notice kind="success" testId="no-leave-types">Your company has not set up any leave types yet.</Notice>
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {balance.map((b) => (
        <div key={b.leave_type} data-testid="leave-balance-card" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-4">
          <p className="text-sm text-[#71717A]">{b.name} · {b.year}</p>
          <p className="mt-1"><span data-testid="balance-remaining" className="text-3xl font-bold text-[#14142B]">{b.remaining}</span> <span className="text-sm text-[#71717A]">of {b.allowed} days left</span></p>
          <p className="text-xs text-[#71717A] mt-1">{b.approved} approved · {b.pending} pending</p>
        </div>
      ))}
    </div>
  )
}

function LeavePage() {
  const [types, setTypes] = useState([])
  const [balance, setBalance] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [status, setStatus] = useState('')
  const load = useCallback((page) => getLeaveRequestsPage(page, status), [status])
  const list = usePagedList(load, status)
  const [cancelling, setCancelling] = useState(null)
  const [busy, setBusy] = useState(false)
  const [cancelError, setCancelError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    let active = true
    Promise.all([getLeaveTypes(), getLeaveBalance()])
      .then(([t, b]) => {
        if (!active) return
        setTypes(t)
        setBalance(b)
      })
      .catch(() => {
        if (active) setError('Failed to load your leave balance.')
      })
    return () => {
      active = false
    }
  }, [refresh])

  const set = (field) => (e) => { setForm((f) => ({ ...f, [field]: e.target.value })); setError('') }
  const days = daysBetween(form.start_date, form.end_date)
  const reversed = days !== null && days < 1
  const endError = reversed ? 'The end date cannot be before the start date.' : ''
  const chosen = balance?.find((b) => b.leave_type === form.leave_type)

  function changed() {
    setRefresh((n) => n + 1)
    list.reload()
  }

  async function submit(e) {
    e.preventDefault()
    setMessage('')
    if (reversed) return // the message is already shown under the end date
    if (!form.leave_type || !form.start_date || !form.end_date || !form.reason.trim()) {
      setError('Choose a leave type, both dates and a reason.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const sent = await applyLeave(form)
      const waiting = sent.approval?.current_step_role_name
      setMessage(`Leave request sent for ${plural(sent.days)}. It is Pending${waiting ? `, waiting for ${waiting}` : ''}.`)
      setForm((f) => ({ ...EMPTY, leave_type: f.leave_type }))
      changed()
    } catch (err) {
      setError(errorText(err, 'Could not send the leave request.'))
    } finally {
      setSaving(false)
    }
  }

  async function confirmCancel() {
    setBusy(true)
    setCancelError('')
    try {
      await cancelLeave(cancelling.id)
      setMessage('The leave request was cancelled. Its days are back in your balance.')
      setCancelling(null)
      changed()
    } catch (err) {
      setCancelError(errorText(err, 'Could not cancel the request.'))
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { key: 'type', label: 'Leave type', render: (r) => <span className="font-medium whitespace-nowrap">{r.leave_type_name}</span> },
    { key: 'dates', label: 'Dates', render: (r) => <span className="whitespace-nowrap">{r.start_date} to {r.end_date}</span> },
    { key: 'days', label: 'Days', render: (r) => r.days },
    { key: 'reason', label: 'Reason', render: (r) => <span className="block max-w-xs">{r.reason}</span> },
    {
      key: 'status', label: 'Status',
      render: (r) => <span data-testid="leave-status"><StatusPill status={STATUS[r.status].variant} label={STATUS[r.status].label} /></span>,
    },
    { key: 'approval', label: 'Approval', render: (r) => <ApprovalProgress approval={r.approval} /> },
    {
      key: 'action', label: 'Action', align: 'right',
      render: (r) => r.status === 'pending' && (
        <button
          type="button" data-testid="cancel-leave" onClick={() => { setCancelling(r); setCancelError('') }}
          className="border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1.5 text-sm font-medium"
        >
          Cancel
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader title="Leave" subtitle="Your balance, a new request, and your requests so far." />
      <BalanceCards balance={balance} />

      <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
        <h2 className="font-semibold text-[#14142B] flex items-center gap-2"><CalendarCheck size={18} className="text-[#6C31D6]" /> Apply for leave</h2>
        <form data-testid="leave-form" onSubmit={submit} noValidate className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
          <label className="text-sm text-[#14142B]">
            Leave type
            <select data-testid="leave-type" required value={form.leave_type} onChange={set('leave_type')} className={input}>
              <option value="">Choose a leave type</option>
              {types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
          <label className="text-sm text-[#14142B]">
            From
            <input data-testid="leave-start" type="date" required value={form.start_date} onChange={set('start_date')} className={input} />
          </label>
          <label className="text-sm text-[#14142B]">
            To
            <input data-testid="leave-end" type="date" required min={form.start_date || undefined} value={form.end_date} onChange={set('end_date')} className={input} />
            {endError && <span data-testid="leave-end-error" role="alert" className="block text-xs text-[#DC2626] mt-1">{endError}</span>}
          </label>
          <label className="text-sm text-[#14142B] md:col-span-3">
            Reason
            <input data-testid="leave-reason" required maxLength={500} value={form.reason} onChange={set('reason')} className={input} />
          </label>
          <div className="md:col-span-3 flex flex-wrap items-center gap-3">
            <button
              type="submit" data-testid="leave-submit" disabled={saving}
              className="bg-[#6C31D6] hover:bg-[#5B27B8] text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60 transition-colors duration-150"
            >
              {saving ? 'Sending...' : 'Send request'}
            </button>
            <p data-testid="leave-days-preview" className="text-sm text-[#71717A]">
              {days && days > 0 ? `${plural(days)} requested` : 'Pick the dates'}
              {chosen && days && days > 0 ? ` · you have ${plural(chosen.remaining)} left in ${chosen.year}` : ''}
            </p>
          </div>
        </form>
        {error && <div className="mt-4"><div data-testid="leave-error" role="alert" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] px-4 py-3 text-sm">{error}</div></div>}
        {message && <div className="mt-4"><Notice kind="success" testId="leave-message">{message}</Notice></div>}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-[#14142B]">My requests</h2>
          <select data-testid="leave-filter" value={status} onChange={(e) => setStatus(e.target.value)} className="border border-[#EEEEF2] rounded-lg px-3 py-1.5 text-sm bg-white">
            {FILTERS.map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
          </select>
        </div>
        {list.error && <Notice>{list.error}</Notice>}
        <DataTable
          testId="leave-table" rowTestId="leave-row" columns={columns} rows={list.data?.items ?? []}
          list={list} page={list.page} onPage={list.setPage} emptyTitle="No leave requests" emptyText="Your requests appear here."
        />
      </div>

      {cancelling && (
        <ConfirmDialog
          title="Cancel this leave request?" confirmLabel="Cancel request" danger busy={busy} error={cancelError}
          onCancel={() => setCancelling(null)} onConfirm={confirmCancel}
        >
          <p>{cancelling.leave_type_name}, {cancelling.start_date} to {cancelling.end_date} ({plural(cancelling.days)}).</p>
          <p>The days go back to your balance.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}

export default LeavePage
