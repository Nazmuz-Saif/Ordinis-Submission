import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, Plus, Pencil, Check, X, Trash2 } from 'lucide-react'
import { getDepartments, createDepartment, updateDepartment, deleteDepartment, getEmployees } from '../../services/organizationService'
import { personName } from '../../utils/people'
import { useAuth } from '../../store/AuthContext'

function DepartmentsPage() {
  const { hasPermission } = useAuth()
  const canManageDepartments = hasPermission('manage_departments')

  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const [editHead, setEditHead] = useState('')
  const [employees, setEmployees] = useState([])

  async function loadDepartments() {
    try {
      const data = await getDepartments()
      setDepartments(data)
    } catch {
      setError('Failed to load departments.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    Promise.resolve().then(loadDepartments)
  }, [])

  useEffect(() => {
    if (!canManageDepartments) return
    getEmployees().then(setEmployees).catch(() => setEmployees([]))
  }, [canManageDepartments])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    try {
      await createDepartment(name)
      setName('')
      loadDepartments()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to create department.')
    }
  }

  function startEdit(dept) {
    setEditingId(dept.id)
    setEditValue(dept.name)
    setEditHead(dept.head || '')
  }

  function cancelEdit() {
    setEditingId(null)
    setEditValue('')
  }

  async function saveEdit(id) {
    setError('')
    try {
      await updateDepartment(id, editValue, editHead)
      setEditingId(null)
      loadDepartments()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update department.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Are you sure you want to delete this department?')) return
    setError('')
    try {
      await deleteDepartment(id)
      loadDepartments()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to delete department.')
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-[#14142B]">Departments</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-6">Organize your company into departments.</p>

      {canManageDepartments && (
<form onSubmit={handleCreate} className="flex gap-2 mb-6">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New department name"
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition w-64"
          required
        />
        <button
          type="submit"
          className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
        >
          <Plus size={16} /> Add
        </button>
      </form>
)}

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : departments.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-14 flex flex-col items-center text-center">
          <Building2 className="text-[#71717A]/40 mb-3" size={36} />
          <p className="text-sm text-[#71717A]">{canManageDepartments ? 'No departments yet. Add your first one above.' : 'No departments yet.'}</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] divide-y divide-[#EEEEF2]">
          {departments.map((dept) => (
            <div
              key={dept.id}
              className="px-4 py-3 flex items-center gap-3 hover:bg-[#FAFAFA] transition-colors duration-150"
            >
              <div className="w-8 h-8 rounded-lg bg-[#6C31D6]/10 text-[#6C31D6] flex items-center justify-center shrink-0">
                <Building2 size={16} />
              </div>

              {editingId === dept.id ? (
                <>
                  <input
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="flex-1 border border-[#6C31D6]/40 rounded-lg px-2 py-1 text-sm outline-none focus:border-[#6C31D6]"
                    autoFocus
                  />
                  <select
                    value={editHead}
                    onChange={(e) => setEditHead(e.target.value)}
                    aria-label="Department head"
                    data-testid="department-head-select"
                    className="border border-[#6C31D6]/40 rounded-lg px-2 py-1 text-sm outline-none focus:border-[#6C31D6] max-w-[200px]"
                  >
                    <option value="">No head</option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>{personName(emp.full_name, emp.user_email)}</option>
                    ))}
                  </select>
                  <button onClick={() => saveEdit(dept.id)} className="text-[#16A34A] hover:opacity-70 transition">
                    <Check size={18} />
                  </button>
                  <button onClick={cancelEdit} className="text-[#71717A] hover:opacity-70 transition">
                    <X size={18} />
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to={`/organization/departments/${dept.id}`}
                    data-testid="department-link"
                    className="flex-1 min-w-0 text-sm text-[#14142B] font-medium hover:text-[#6C31D6] transition-colors truncate"
                  >
                    {dept.name}
                  </Link>
                  <span className="hidden sm:block text-xs text-[#71717A] shrink-0" data-testid="department-head">
                    {dept.head ? `Head: ${personName(dept.head_name, dept.head_email)}` : 'No head'}
                  </span>
                  <span className="text-xs text-[#71717A] shrink-0 w-24 text-right" data-testid="department-count">
                    {dept.member_count} {dept.member_count === 1 ? 'person' : 'people'}
                  </span>
                  {canManageDepartments && (
<div className="flex items-center gap-1">
                    <button onClick={() => startEdit(dept)} className="text-[#71717A] hover:text-[#6C31D6] p-1 transition" title="Edit">
                      <Pencil size={15} />
                    </button>
                    <button onClick={() => handleDelete(dept.id)} className="text-[#71717A] hover:text-[#DC2626] p-1 transition" title="Delete">
                      <Trash2 size={15} />
                    </button>
                  </div>
)}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DepartmentsPage