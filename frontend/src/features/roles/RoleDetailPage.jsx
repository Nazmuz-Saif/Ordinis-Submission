import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Lock, Pencil, Shield, Trash2 } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getPermissions, getRole, updateRole, deleteRole } from '../../services/rolesService'
import PermissionPicker from '../../components/roles/PermissionPicker'
import { errorMessage, groupByModule, moduleLabel } from './roleFormat'
import { personName } from '../../utils/people'

const SYSTEM_NOTE =
  'The CEO system Role always holds every Permission so the company can never lock itself out. It cannot be edited or deleted.'

function RoleDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const canManage = hasPermission('manage_roles')

  const [role, setRole] = useState(null)
  const [allPermissions, setAllPermissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selected, setSelected] = useState([])
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      const [data, perms] = await Promise.all([getRole(id), getPermissions()])
      setRole(data)
      setAllPermissions(perms || [])
    } catch (err) {
      if (err.response?.status === 404) setNotFound(true)
      else setError(errorMessage(err, 'Failed to load this Role.'))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    Promise.resolve().then(load)
  }, [load])

  function startEdit() {
    setName(role.name)
    setDescription(role.description || '')
    setSelected((role.permission_details || []).map((p) => p.id))
    setError('')
    setSuccess('')
    setEditing(true)
  }

  async function handleSave(e) {
    e.preventDefault()
    if (!name.trim()) {
      setError('Enter a Role name.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const saved = await updateRole(id, { name: name.trim(), description, permissions: selected })
      const savedCount = (saved?.permissions || []).length
      if (savedCount !== selected.length) {
        setError(`The server saved ${savedCount} of the ${selected.length} Permissions you ticked. Check the list below.`)
      } else {
        setSuccess('Role saved.')
      }
      setEditing(false)
      await load()
    } catch (err) {
      setError(errorMessage(err, 'Failed to save the Role.'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete the Role "${role.name}"?`)) return
    setError('')
    try {
      await deleteRole(id)
      navigate('/roles')
    } catch (err) {
      setError(errorMessage(err, 'Failed to delete the Role.'))
    }
  }

  if (loading) return <p className="text-sm text-[#71717A]">Loading…</p>
  if (notFound) {
    return (
      <div>
        <Link to="/roles" className="inline-flex items-center gap-1 text-sm text-[#6C31D6] mb-4"><ArrowLeft size={14} /> Roles</Link>
        <p className="text-sm text-[#71717A]">This Role does not exist.</p>
      </div>
    )
  }
  if (!role) return error ? <p className="text-sm text-red-600">{error}</p> : null

  const count = role.employee_count || 0
  const inputClass = 'border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition w-full'

  return (
    <div className="pb-12 max-w-4xl">
      <Link to="/roles" className="inline-flex items-center gap-1 text-sm text-[#6C31D6] mb-4">
        <ArrowLeft size={14} /> Roles
      </Link>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">{error}</div>}
      {success && <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">{success}</div>}

      <div className="bg-white rounded-xl border border-[#EEEEF2] p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield size={20} className="text-[#6C31D6]" />
            <h1 className="text-2xl font-bold text-[#14142B]">{role.name}</h1>
            {role.is_system_default && (
              <span className="text-[10px] bg-[#6C31D6]/10 text-[#6C31D6] px-1.5 py-0.5 rounded font-medium">System</span>
            )}
          </div>
          {canManage && !role.is_system_default && !editing && (
            <div className="flex gap-2">
              <button onClick={startEdit} className="flex items-center gap-1.5 border border-[#EEEEF2] hover:bg-[#FAFAFA] rounded-lg px-3 py-1.5 text-sm text-[#14142B] transition">
                <Pencil size={14} /> Edit
              </button>
              <button onClick={handleDelete} className="flex items-center gap-1.5 border border-[#EEEEF2] hover:bg-red-50 rounded-lg px-3 py-1.5 text-sm text-[#DC2626] transition">
                <Trash2 size={14} /> Delete
              </button>
            </div>
          )}
        </div>
        {!editing && (
          <p className="text-sm text-[#71717A] mt-2">{role.description || 'No description.'}</p>
        )}
        <p className="text-xs text-[#71717A] mt-2">
          {count} employee{count === 1 ? '' : 's'} hold{count === 1 ? 's' : ''} this Role · {(role.permission_details || []).length} Permission{(role.permission_details || []).length === 1 ? '' : 's'}
        </p>
        {role.is_system_default && (
          <p className="mt-3 flex items-start gap-2 text-xs text-[#71717A] bg-[#FAFAFA] border border-[#EEEEF2] rounded-lg p-3" data-testid="system-role-note">
            <Lock size={14} className="mt-0.5 shrink-0" /> {SYSTEM_NOTE}
          </p>
        )}
      </div>

      {editing ? (
        <form onSubmit={handleSave} className="bg-white rounded-xl border border-[#EEEEF2] p-6 mb-6">
          <h2 className="text-base font-semibold text-[#14142B] mb-4">Edit Role</h2>
          <label className="block text-xs text-[#71717A] mb-1">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className={`${inputClass} max-w-sm mb-4`} required />
          <label className="block text-xs text-[#71717A] mb-1">Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={`${inputClass} mb-4`} />
          <PermissionPicker permissions={allPermissions} selected={selected} onChange={setSelected} />
          <p className="text-sm text-[#14142B] bg-[#F1EEFB] rounded-lg px-3 py-2 mt-4" data-testid="affect-note">
            {count > 0
              ? `Saving changes the access of ${count} employee${count === 1 ? '' : 's'} who hold${count === 1 ? 's' : ''} this Role.`
              : 'No employee holds this Role yet, so saving changes nobody’s access.'}
          </p>
          <div className="flex gap-2 mt-4">
            <button type="submit" disabled={saving} className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 text-white rounded-lg px-5 py-2 text-sm font-medium transition">
              {saving ? 'Saving…' : 'Save changes'}
            </button>
            <button type="button" onClick={() => setEditing(false)} className="border border-[#EEEEF2] rounded-lg px-5 py-2 text-sm text-[#14142B]">
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="bg-white rounded-xl border border-[#EEEEF2] p-6 mb-6">
          <h2 className="text-base font-semibold text-[#14142B] mb-4">What this Role allows</h2>
          {(role.permission_details || []).length === 0 ? (
            <p className="text-sm text-[#A1A1AA] italic">This Role has no Permissions yet.</p>
          ) : (
            groupByModule(role.permission_details).map(([module, perms]) => (
              <div key={module} className="mb-4">
                <p className="text-xs uppercase tracking-wide text-[#A1A1AA] mb-1.5">{moduleLabel(module)}</p>
                <ul className="space-y-2">
                  {perms.map((p) => (
                    <li key={p.id}>
                      <span className="text-sm font-medium text-[#14142B]">{p.name}</span>
                      <span className="block text-xs text-[#71717A]">{p.description}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))
          )}
        </div>
      )}

      <div className="bg-white rounded-xl border border-[#EEEEF2] p-6">
        <h2 className="text-base font-semibold text-[#14142B] mb-3">Employees who hold this Role</h2>
        {(role.employees || []).length === 0 ? (
          <p className="text-sm text-[#A1A1AA] italic">Nobody holds this Role yet.</p>
        ) : (
          <ul className="divide-y divide-[#EEEEF2]">
            {role.employees.map((e) => (
              <li key={e.id} className="py-2 text-sm">
                <Link to={`/organization/employees/${e.id}`} className="text-[#6C31D6] hover:underline">{personName(e.name, e.email)}</Link>
                <span className="text-[#71717A]"> · {e.employee_code}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default RoleDetailPage
