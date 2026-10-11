import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Trash2 } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getEmployees } from '../../services/organizationService'
import { generatePayslip, getPayslipsPage, voidPayslip } from '../../services/payrollService'
import EmptyState from '../../components/common/EmptyState'
import { ConfirmDialog, DataTable, Notice, PageHeader } from '../admin/shared'
import { usePagedList } from '../admin/usePagedList'
import { currentMonth, errorText, formatMoney } from './payslipFormat'

const input = 'mt-1 w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm bg-white outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15'

function GenerateCard({ employees, onCreated }) {
  const [form, setForm] = useState({ employee: '', month: currentMonth(), deductions: '', deduction_note: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setResult(null)
    try {
      const payload = { employee: form.employee, month: form.month }
      if (form.deductions !== '') payload.deductions = form.deductions
      if (form.deduction_note.trim()) payload.deduction_note = form.deduction_note
      const payslip = await generatePayslip(payload)
      setResult(payslip)
      setForm((f) => ({ ...f, deductions: '', deduction_note: '' }))
      onCreated()
    } catch (err) {
      setError(errorText(err, 'Could not generate the payslip.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
      <h2 className="font-semibold text-[#14142B]">Generate a payslip</h2>
      <form data-testid="payslip-form" onSubmit={submit} className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-3 items-end">
        <label className="text-sm text-[#14142B]">
          Employee
          <select data-testid="payslip-employee" required value={form.employee} onChange={set('employee')} className={input}>
            <option value="">Choose an employee</option>
            {employees.map((e) => <option key={e.id} value={e.id}>{e.employee_code} · {e.email}</option>)}
          </select>
        </label>
        <label className="text-sm text-[#14142B]">
          Month
          <input data-testid="payslip-month" type="month" required value={form.month} onChange={set('month')} className={input} />
        </label>
        <label className="text-sm text-[#14142B]">
          Deductions (optional)
          <input data-testid="payslip-deductions" type="number" min="0" step="0.01" placeholder="0.00" value={form.deductions} onChange={set('deductions')} className={input} />
        </label>
        <label className="text-sm text-[#14142B]">
          Deduction note (optional)
          <input data-testid="payslip-note" maxLength={255} value={form.deduction_note} onChange={set('deduction_note')} className={input} />
        </label>
        <div className="md:col-span-4 flex items-center gap-3">
          <button
            type="submit" data-testid="payslip-generate" disabled={saving}
            className="bg-[#6C31D6] hover:bg-[#5B27B8] text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60 transition-colors duration-150"
          >
            {saving ? 'Generating...' : 'Generate payslip'}
          </button>
          <p className="text-xs text-[#71717A]">Amounts come from the employee&apos;s Salary Structure. One payslip per employee and month.</p>
        </div>
      </form>

      {error && <div className="mt-4"><div data-testid="payslip-error" role="alert" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] px-4 py-3 text-sm">{error}</div></div>}

      {result && (
        <div data-testid="payslip-result" className="mt-4 rounded-xl border border-[#16A34A]/30 bg-[#16A34A]/5 p-4">
          <p className="text-sm font-medium text-[#15803D]">Payslip generated for {result.employee_email}, {result.month_label}.</p>
          <dl className="grid grid-cols-3 gap-4 mt-3 text-sm">
            <div><dt className="text-[#71717A]">Gross</dt><dd data-testid="result-gross" className="font-semibold text-[#14142B]">{formatMoney(result.gross_amount, result.currency)}</dd></div>
            <div><dt className="text-[#71717A]">Deductions</dt><dd data-testid="result-deductions" className="font-semibold text-[#14142B]">{formatMoney(result.deductions, result.currency)}</dd></div>
            <div><dt className="text-[#71717A]">Net pay</dt><dd data-testid="result-net" className="font-semibold text-[#14142B]">{formatMoney(result.net_amount, result.currency)}</dd></div>
          </dl>
          <Link to={`/payroll/payslips/${result.id}`} className="inline-block mt-3 text-sm font-medium text-[#6C31D6] hover:underline">Open the payslip</Link>
        </div>
      )}
    </div>
  )
}

function PayslipsPage() {
  const { hasPermission } = useAuth()
  const allowed = hasPermission('manage_finance')

  const [month, setMonth] = useState('')
  const load = useCallback((page) => getPayslipsPage(page, { month }), [month])
  const list = usePagedList(load, month)
  const [employees, setEmployees] = useState([])
  const [voiding, setVoiding] = useState(null)
  const [busy, setBusy] = useState(false)
  const [voidError, setVoidError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!allowed) return
    getEmployees().then(setEmployees).catch(() => setEmployees([]))
  }, [allowed])

  async function confirmVoid() {
    setBusy(true)
    setVoidError('')
    try {
      await voidPayslip(voiding.id)
      setMessage(`The payslip of ${voiding.employee_email} for ${voiding.month_label} was voided. You can generate it again.`)
      setVoiding(null)
      list.reload()
    } catch (err) {
      setVoidError(errorText(err, 'Could not void the payslip.'))
    } finally {
      setBusy(false)
    }
  }

  if (!allowed) {
    return <EmptyState icon={FileText} title="You do not have access to this page" description="Generating payslips needs the Manage Finance permission." />
  }

  const columns = [
    { key: 'employee', label: 'Employee', render: (p) => (<><p className="font-medium">{p.employee_email}</p><p className="text-xs text-[#71717A]">{p.employee_code}</p></>) },
    { key: 'month', label: 'Month', render: (p) => <span className="whitespace-nowrap">{p.month_label}</span> },
    { key: 'gross', label: 'Gross', render: (p) => formatMoney(p.gross_amount, p.currency) },
    { key: 'deductions', label: 'Deductions', render: (p) => formatMoney(p.deductions, p.currency) },
    { key: 'net', label: 'Net pay', render: (p) => <span className="font-semibold">{formatMoney(p.net_amount, p.currency)}</span> },
    {
      key: 'action', label: 'Action', align: 'right',
      render: (p) => (
        <div className="flex justify-end gap-2">
          <Link to={`/payroll/payslips/${p.id}`} data-testid="view-payslip" className="border border-[#EEEEF2] hover:bg-[#FAFAFA] rounded-lg px-3 py-1.5 text-sm font-medium text-[#14142B]">View</Link>
          <button type="button" data-testid="void-payslip" onClick={() => { setVoiding(p); setVoidError('') }} className="flex items-center gap-1 border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1.5 text-sm font-medium">
            <Trash2 size={14} /> Void
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-5">
      <PageHeader title="Payslips" subtitle="Generate a payslip for one employee and month, and see every payslip in the company." />
      {message && <Notice kind="success" testId="payslip-message">{message}</Notice>}
      <GenerateCard employees={employees} onCreated={list.reload} />

      <div className="flex items-end gap-3">
        <label className="text-sm text-[#14142B]">
          Show month
          <input data-testid="filter-month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} className={input + ' w-48'} />
        </label>
        {month && <button type="button" data-testid="clear-month" onClick={() => setMonth('')} className="text-sm text-[#6C31D6] hover:underline pb-2">Show all months</button>}
      </div>

      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="payslips-table" rowTestId="payslip-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage} emptyTitle="No payslips" emptyText="Generated payslips appear here."
      />

      {voiding && (
        <ConfirmDialog
          title="Void this payslip?" confirmLabel="Void payslip" danger busy={busy} error={voidError}
          onCancel={() => setVoiding(null)} onConfirm={confirmVoid}
        >
          <p>{voiding.employee_email}, {voiding.month_label}: net pay {formatMoney(voiding.net_amount, voiding.currency)}.</p>
          <p>The employee will no longer see it. You can then generate the month again.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}

export default PayslipsPage
