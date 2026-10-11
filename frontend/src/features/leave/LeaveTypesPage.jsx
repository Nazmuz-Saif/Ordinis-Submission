import { useEffect, useState } from 'react'
import { CalendarDays, Check, Pencil, Trash2, X } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { createLeaveType, deleteLeaveType, getLeaveTypes, updateLeaveType } from '../../services/leaveService'
import EmptyState from '../../components/common/EmptyState'
import { ConfirmDialog, Notice, PageHeader } from '../admin/shared'
import { errorText } from './leaveFormat'

const input = 'border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm bg-white outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15'

function fieldMessage(err, fallback) {
  const fields = err.response?.data?.error?.field_errors || {}
  const first = Object.values(fields)[0]
  return (Array.isArray(first) ? first[0] : first) || errorText(err, fallback)
}

function LeaveTypesPage() {
  const { hasPermission } = useAuth()
  const allowed = hasPermission('manage_leave_types')

  const [types, setTypes] = useState(null)
  const [refresh, setRefresh] = useState(0)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState({ name: '', days_allowed_per_year: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [editing, setEditing] = useState(null) // { id, name, days }
  const [editError, setEditError] = useState('')
  const [deleting, setDeleting] = useState(null)
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    if (!allowed) return
    let active = true
    getLeaveTypes()
      .then((data) => { if (active) setTypes(data) })
      .catch(() => { if (active) setLoadError('Failed to load the leave types.') })
    return () => { active = false }
  }, [allowed, refresh])

  const reload = () => setRefresh((n) => n + 1)

  async function add(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await createLeaveType({ name: form.name, days_allowed_per_year: form.days_allowed_per_year === '' ? 0 : Number(form.days_allowed_per_year) })
      setMessage(`${form.name.trim()} was added.`)
      setForm({ name: '', days_allowed_per_year: '' })
      reload()
    } catch (err) {
      setError(fieldMessage(err, 'Could not add the leave type.'))
    }
  }

  async function save() {
    setEditError('')
    try {
      await updateLeaveType(editing.id, { name: editing.name, days_allowed_per_year: Number(editing.days) })
      setEditing(null)
      reload()
    } catch (err) {
      setEditError(fieldMessage(err, 'Could not save the change.'))
    }
  }

  async function confirmDelete() {
    setDeleteError('')
    try {
      await deleteLeaveType(deleting.id)
      setMessage(`${deleting.name} was deleted.`)
      setDeleting(null)
      reload()
    } catch (err) {
      setDeleteError(errorText(err, 'Could not delete the leave type.'))
    }
  }

  if (!allowed) {
    return <EmptyState icon={CalendarDays} title="You do not have access to this page" description="Managing leave types needs the Manage Leave Types permission." />
  }

  return (
    <div className="space-y-5">
      <PageHeader title="Leave types" subtitle="The kinds of leave your company offers and how many days a year each allows. Changing the days changes everyone's balance at once." />
      {message && <Notice kind="success" testId="lt-message">{message}</Notice>}
      {loadError && <Notice>{loadError}</Notice>}

      <form data-testid="leavetype-form" onSubmit={add} className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-4 flex flex-wrap items-end gap-3">
        <label className="text-sm text-[#14142B]">Name
          <input data-testid="lt-name" required maxLength={60} value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} className={input + ' block mt-1'} />
        </label>
        <label className="text-sm text-[#14142B]">Days a year
          <input data-testid="lt-days" type="number" min="0" max="366" required value={form.days_allowed_per_year} onChange={(e) => setForm((f) => ({ ...f, days_allowed_per_year: e.target.value }))} className={input + ' block mt-1 w-32'} />
        </label>
        <button type="submit" data-testid="lt-add" className="bg-[#6C31D6] hover:bg-[#5B27B8] text-white rounded-lg px-4 py-2 text-sm font-medium">Add leave type</button>
        {error && <p data-testid="lt-error" role="alert" className="w-full text-sm text-[#DC2626]">{error}</p>}
      </form>

      {!types && !loadError && <div className="skeleton h-32 w-full rounded-xl" />}
      {types && types.length === 0 && <EmptyState title="No leave types yet" description="Add one above, for example Annual Leave with 15 days." />}
      {types && types.length > 0 && (
        <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm overflow-x-auto">
          <table data-testid="lt-table" className="w-full text-sm">
            <thead><tr className="text-left text-[#71717A] border-b border-[#EEEEF2]">
              <th className="px-4 py-3 font-medium">Name</th><th className="px-4 py-3 font-medium">Days a year</th><th className="px-4 py-3 font-medium text-right">Action</th>
            </tr></thead>
            <tbody className="divide-y divide-[#EEEEF2]">
              {types.map((t) => editing?.id === t.id ? (
                <tr key={t.id} data-testid="lt-row" className="bg-[#FAFAFA]">
                  <td className="px-4 py-2"><input data-testid="lt-edit-name" value={editing.name} onChange={(e) => setEditing((x) => ({ ...x, name: e.target.value }))} className={input + ' w-full'} /></td>
                  <td className="px-4 py-2"><input data-testid="lt-edit-days" type="number" min="0" max="366" value={editing.days} onChange={(e) => setEditing((x) => ({ ...x, days: e.target.value }))} className={input + ' w-28'} /></td>
                  <td className="px-4 py-2">
                    <div className="flex justify-end gap-2 items-center">
                      {editError && <span data-testid="lt-edit-error" role="alert" className="text-xs text-[#DC2626]">{editError}</span>}
                      <button type="button" data-testid="lt-save" onClick={save} aria-label="Save" className="p-1.5 rounded-lg text-[#16A34A] hover:bg-[#16A34A]/10"><Check size={16} /></button>
                      <button type="button" onClick={() => setEditing(null)} aria-label="Cancel edit" className="p-1.5 rounded-lg text-[#71717A] hover:bg-white"><X size={16} /></button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={t.id} data-testid="lt-row" className="text-[#14142B]">
                  <td className="px-4 py-3 font-medium">{t.name}</td>
                  <td className="px-4 py-3">{t.days_allowed_per_year}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button type="button" data-testid="lt-edit" onClick={() => { setEditing({ id: t.id, name: t.name, days: t.days_allowed_per_year }); setEditError('') }} aria-label={`Edit ${t.name}`} className="p-1.5 rounded-lg text-[#6C31D6] hover:bg-[#EDE9FE]"><Pencil size={16} /></button>
                      <button type="button" data-testid="lt-delete" onClick={() => { setDeleting(t); setDeleteError('') }} aria-label={`Delete ${t.name}`} className="p-1.5 rounded-lg text-[#DC2626] hover:bg-[#DC2626]/10"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {deleting && (
        <ConfirmDialog title={`Delete ${deleting.name}?`} confirmLabel="Delete leave type" danger error={deleteError} onCancel={() => setDeleting(null)} onConfirm={confirmDelete}>
          <p>A leave type that already has requests cannot be deleted. Set its days to 0 to stop new requests instead.</p>
        </ConfirmDialog>
      )}
    </div>
  )
}

export default LeaveTypesPage
