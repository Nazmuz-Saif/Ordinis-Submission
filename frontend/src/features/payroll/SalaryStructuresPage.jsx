import { useEffect, useState } from 'react'
import { Lock, Pencil, Plus, Trash2, Wallet, X } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getEmployees } from '../../services/organizationService'
import {
  getSalaryStructures, createSalaryStructure, updateSalaryStructure, deleteSalaryStructure,
} from '../../services/payrollService'
import EmptyState from '../../components/common/EmptyState'

const inputClass =
  'w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition'

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

function money(value) {
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function toRows(allowances) {
  return Object.entries(allowances || {}).map(([name, amount]) => ({ name, amount: String(amount) }))
}

function SalaryStructuresPage() {
  const { hasPermission } = useAuth()
  const allowed = hasPermission('manage_finance')

  const [items, setItems] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(allowed)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  // form modal: null = closed
  const [form, setForm] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  async function reload() {
    try {
      setItems(await getSalaryStructures())
    } catch (err) {
      setError(errorMessage(err, 'Failed to load salary structures.'))
    }
  }

  useEffect(() => {
    if (!allowed) return undefined
    let active = true
    Promise.all([getSalaryStructures(), getEmployees()])
      .then(([structureData, employeeData]) => {
        if (!active) return
        setItems(structureData)
        setEmployees(employeeData)
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, 'Failed to load salary structures.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [allowed])

  if (!allowed) {
    return (
      <div data-testid="salary-no-access" className="bg-white rounded-xl border border-[#EEEEF2] py-14 flex flex-col items-center text-center">
        <Lock className="text-[#71717A]/50 mb-3" size={34} />
        <h1 className="text-lg font-semibold text-[#14142B]">Salary data is restricted</h1>
        <p className="text-sm text-[#71717A] mt-1 max-w-sm">
          You need the finance permission to see salary structures. Ask your administrator if you need access.
        </p>
      </div>
    )
  }

  const withStructure = new Set(items.map((s) => s.employee))
  const available = employees.filter((e) => editingId || !withStructure.has(e.id))

  function openCreate() {
    setEditingId(null)
    setForm({ employee: '', base_salary: '', allowances: [] })
    setFormError('')
  }

  function openEdit(item) {
    setEditingId(item.id)
    setForm({ employee: item.employee, base_salary: String(item.base_salary), allowances: toRows(item.allowances) })
    setFormError('')
  }

  const setField = (name) => (e) => setForm((prev) => ({ ...prev, [name]: e.target.value }))

  function setAllowance(index, field, value) {
    setForm((prev) => ({
      ...prev,
      allowances: prev.allowances.map((row, i) => (i === index ? { ...row, [field]: value } : row)),
    }))
  }

  function addAllowance() {
    setForm((prev) => ({ ...prev, allowances: [...prev.allowances, { name: '', amount: '' }] }))
  }

  function removeAllowance(index) {
    setForm((prev) => ({ ...prev, allowances: prev.allowances.filter((_, i) => i !== index) }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setFormError('')

    const allowances = {}
    for (const row of form.allowances) {
      const name = row.name.trim()
      if (!name && row.amount === '') continue // an untouched row
      if (!name) {
        setFormError('Every allowance needs a name.')
        return
      }
      if (name in allowances) {
        setFormError(`The allowance "${name}" appears twice.`)
        return
      }
      allowances[name] = row.amount === '' ? 0 : Number(row.amount)
    }

    setSaving(true)
    try {
      if (editingId) {
        await updateSalaryStructure(editingId, { base_salary: form.base_salary, allowances })
      } else {
        await createSalaryStructure({ employee: form.employee, base_salary: form.base_salary, allowances })
      }
      setForm(null)
      setMessage(editingId ? 'Salary structure updated.' : 'Salary structure created.')
      await reload()
    } catch (err) {
      setFormError(errorMessage(err, 'Failed to save the salary structure.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(item) {
    if (!confirm(`Delete the salary structure of ${item.employee_email}?`)) return
    setError('')
    setMessage('')
    try {
      await deleteSalaryStructure(item.id)
      setMessage('Salary structure deleted.')
      await reload()
    } catch (err) {
      setError(errorMessage(err, 'Failed to delete the salary structure.'))
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-[#14142B]">Salary Structures</h1>
        <button
          onClick={openCreate}
          data-testid="new-salary-button"
          className="ml-auto flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
        >
          <Plus size={16} /> New Salary Structure
        </button>
      </div>
      <p className="text-sm text-[#71717A] mb-5">
        Confidential. Only people with the finance permission see this page, whatever their position in the company.
      </p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}
      {message && <p className="text-sm text-[#16A34A] mb-4">{message}</p>}

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Wallet}
          title="No salary structures yet"
          description="Define a base salary and allowances for an employee."
          actionLabel="New Salary Structure"
          onAction={openCreate}
        />
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[#71717A] border-b border-[#EEEEF2]">
                <th className="px-4 py-3 font-medium">Employee</th>
                <th className="px-4 py-3 font-medium text-right">Base salary</th>
                <th className="px-4 py-3 font-medium">Allowances</th>
                <th className="px-4 py-3 font-medium text-right">Gross</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEEEF2]">
              {items.map((item) => (
                <tr key={item.id} data-testid="salary-row" className="hover:bg-[#FAFAFA] transition-colors duration-150">
                  <td className="px-4 py-3">
                    <p className="font-medium text-[#14142B]">{item.employee_email}</p>
                    <p className="text-xs text-[#71717A]">{item.employee_code}</p>
                  </td>
                  <td className="px-4 py-3 text-right text-[#14142B]">{money(item.base_salary)}</td>
                  <td className="px-4 py-3 text-[#14142B]">
                    {Object.keys(item.allowances).length === 0 ? (
                      <span className="text-[#71717A]">-</span>
                    ) : (
                      Object.entries(item.allowances).map(([name, amount]) => (
                        <span key={name} className="inline-block mr-2 text-xs bg-[#EDE9FE] text-[#6C31D6] rounded-full px-2 py-0.5">
                          {name}: {money(amount)}
                        </span>
                      ))
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-[#14142B]">{money(item.gross_amount)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => openEdit(item)}
                        title="Edit"
                        data-testid="edit-salary"
                        className="p-1.5 rounded-lg text-[#71717A] hover:bg-[#FAFAFA] hover:text-[#6C31D6] transition-colors"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        onClick={() => handleDelete(item)}
                        title="Delete"
                        data-testid="delete-salary"
                        className="p-1.5 rounded-lg text-[#71717A] hover:bg-[#FAFAFA] hover:text-[#DC2626] transition-colors"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {form && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14142B]/40 p-4">
          <form onSubmit={handleSave} data-testid="salary-form" className="bg-white rounded-xl shadow-xl w-full max-w-lg p-5 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-[#14142B] mb-4">
              {editingId ? 'Edit salary structure' : 'New salary structure'}
            </h2>

            <label className="block text-sm font-medium text-[#14142B] mb-1">Employee</label>
            {editingId ? (
              <p className="text-sm text-[#14142B] mb-3">
                {items.find((i) => i.id === editingId)?.employee_email}
              </p>
            ) : (
              <select
                value={form.employee}
                onChange={setField('employee')}
                required
                data-testid="salary-employee"
                className={`${inputClass} mb-3`}
              >
                <option value="">Choose an employee...</option>
                {available.map((emp) => (
                  <option key={emp.id} value={emp.id}>{`${emp.user_email} · ${emp.employee_code}`}</option>
                ))}
              </select>
            )}

            <label className="block text-sm font-medium text-[#14142B] mb-1">Base salary</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.base_salary}
              onChange={setField('base_salary')}
              required
              data-testid="salary-base"
              className={`${inputClass} mb-4`}
            />

            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-[#14142B]">Allowances</label>
              <button
                type="button"
                onClick={addAllowance}
                data-testid="add-allowance"
                className="flex items-center gap-1 text-xs text-[#6C31D6] hover:underline"
              >
                <Plus size={13} /> Add allowance
              </button>
            </div>
            {form.allowances.length === 0 && <p className="text-xs text-[#71717A] mb-2">No allowances.</p>}
            <div className="space-y-2">
              {form.allowances.map((row, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <input
                    value={row.name}
                    onChange={(e) => setAllowance(index, 'name', e.target.value)}
                    placeholder="Name (e.g. House Rent)"
                    data-testid="salary-allowance-name"
                    className={inputClass}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={row.amount}
                    onChange={(e) => setAllowance(index, 'amount', e.target.value)}
                    placeholder="Amount"
                    data-testid="salary-allowance-amount"
                    className={`${inputClass} w-32`}
                  />
                  <button
                    type="button"
                    onClick={() => removeAllowance(index)}
                    title="Remove allowance"
                    className="p-1.5 text-[#71717A] hover:text-[#DC2626]"
                  >
                    <X size={15} />
                  </button>
                </div>
              ))}
            </div>

            {formError && <p data-testid="salary-error" className="text-sm text-[#DC2626] mt-3">{formError}</p>}

            <div className="flex justify-end gap-2 mt-5">
              <button type="button" onClick={() => setForm(null)} className="px-4 py-2 text-sm text-[#71717A] hover:text-[#14142B]">
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                data-testid="salary-save"
                className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              >
                {editingId ? 'Save changes' : 'Create'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

export default SalaryStructuresPage
