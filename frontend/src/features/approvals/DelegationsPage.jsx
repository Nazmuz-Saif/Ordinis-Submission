import { useEffect, useState } from 'react'
import { CalendarDays, Trash2, UserCheck } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getEmployees } from '../../services/organizationService'
import { getDelegations, createDelegation, deleteDelegation } from '../../services/approvalsService'
import StatusPill from '../../components/common/StatusPill'
import EmptyState from '../../components/common/EmptyState'

const EMPTY_FORM = { delegate: '', start_date: '', end_date: '', reason: '' }

const inputClass =
  'w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition'

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

function periodStatus(rule) {
  const now = today()
  if (rule.end_date < now) return { status: 'neutral', label: 'Expired' }
  if (rule.start_date > now) return { status: 'info', label: 'Upcoming' }
  return { status: 'success', label: 'Active' }
}

function DelegationsPage() {
  const { me } = useAuth()
  const [rules, setRules] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [form, setForm] = useState({ ...EMPTY_FORM })
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  async function reload() {
    try {
      setRules(await getDelegations())
    } catch (err) {
      setError(errorMessage(err, 'Failed to load delegations.'))
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([getDelegations(), getEmployees()])
      .then(([ruleData, employeeData]) => {
        if (!active) return
        setRules(ruleData)
        setEmployees(employeeData)
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, 'Failed to load delegations.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const setField = (name) => (e) => setForm((prev) => ({ ...prev, [name]: e.target.value }))

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    setMessage('')
    try {
      await createDelegation(form)
      setForm({ ...EMPTY_FORM })
      setMessage('Delegation created.')
      await reload()
    } catch (err) {
      setFormError(errorMessage(err, 'Failed to create the delegation.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(rule) {
    if (!confirm('Remove this delegation? The delegate loses the authority immediately.')) return
    setError('')
    setMessage('')
    try {
      await deleteDelegation(rule.id)
      setMessage('Delegation removed.')
      await reload()
    } catch (err) {
      setError(errorMessage(err, 'Failed to remove the delegation.'))
    }
  }

  const colleagues = employees.filter((emp) => emp.id !== me?.employee_id)

  return (
    <div>
      <h1 className="text-2xl font-bold text-[#14142B]">Delegation</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-5">
        While you are away, let a colleague decide the requests that wait for your roles. The delegation is active
        from the start date to the end date, both included.
      </p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}
      {message && <p className="text-sm text-[#16A34A] mb-4">{message}</p>}

      <form
        onSubmit={handleSave}
        data-testid="delegation-form"
        className="bg-white rounded-xl border border-[#EEEEF2] p-4 mb-6 grid grid-cols-1 md:grid-cols-4 gap-3 items-end"
      >
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-[#14142B] mb-1">Delegate to</label>
          <select
            value={form.delegate}
            onChange={setField('delegate')}
            required
            data-testid="delegation-delegate"
            className={inputClass}
          >
            <option value="">Choose a colleague...</option>
            {colleagues.map((emp) => (
              <option key={emp.id} value={emp.id}>{`${emp.user_email} · ${emp.employee_code}`}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-[#14142B] mb-1">Start date</label>
          <input
            type="date"
            value={form.start_date}
            onChange={setField('start_date')}
            required
            data-testid="delegation-start"
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-[#14142B] mb-1">End date</label>
          <input
            type="date"
            value={form.end_date}
            onChange={setField('end_date')}
            required
            data-testid="delegation-end"
            className={inputClass}
          />
        </div>
        <div className="md:col-span-3">
          <label className="block text-sm font-medium text-[#14142B] mb-1">Reason (optional)</label>
          <input value={form.reason} onChange={setField('reason')} placeholder="e.g. On leave" className={inputClass} />
        </div>
        <button
          type="submit"
          disabled={saving}
          data-testid="delegation-save"
          className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
        >
          Create delegation
        </button>
        {formError && (
          <p data-testid="delegation-error" className="md:col-span-4 text-sm text-[#DC2626]">{formError}</p>
        )}
      </form>

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : rules.length === 0 ? (
        <EmptyState
          icon={UserCheck}
          title="No delegations yet"
          description="Create one above when you will be away."
        />
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[#71717A] border-b border-[#EEEEF2]">
                <th className="px-4 py-3 font-medium">Direction</th>
                <th className="px-4 py-3 font-medium">Delegator</th>
                <th className="px-4 py-3 font-medium">Delegate</th>
                <th className="px-4 py-3 font-medium">Period</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEEEF2]">
              {rules.map((rule) => {
                const mine = rule.delegator === me?.employee_id
                const period = periodStatus(rule)
                return (
                  <tr key={rule.id} data-testid="delegation-row" className="hover:bg-[#FAFAFA] transition-colors duration-150">
                    <td className="px-4 py-3 text-[#14142B]">{mine ? 'Given by me' : 'Given to me'}</td>
                    <td className="px-4 py-3 text-[#14142B]">{rule.delegator_email}</td>
                    <td className="px-4 py-3 text-[#14142B]">{rule.delegate_email}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-[#14142B]">
                      <span className="inline-flex items-center gap-1">
                        <CalendarDays size={13} aria-hidden="true" />
                        {rule.start_date} → {rule.end_date}
                      </span>
                      {rule.reason && <p className="text-xs text-[#71717A]">{rule.reason}</p>}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={period.status} label={period.label} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      {mine && (
                        <button
                          onClick={() => handleDelete(rule)}
                          title="Remove delegation"
                          data-testid="delete-delegation"
                          className="p-1.5 rounded-lg text-[#71717A] hover:bg-[#FAFAFA] hover:text-[#DC2626] transition-colors"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default DelegationsPage
