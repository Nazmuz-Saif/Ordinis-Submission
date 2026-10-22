import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Lock, Pencil, Shield, Trash2, UserPlus, Users } from 'lucide-react'
import {
  getEmployee,
  getEmployeeAccess,
  updateEmployee,
  getEmployeeRoles,
  assignEmployeeRole,
  deleteEmployeeRole,
} from '../../services/organizationService'
import { getRoles } from '../../services/rolesService'
import { useAuth } from '../../store/AuthContext'
import { personName } from '../../utils/people'
import { groupByModule, moduleLabel } from '../roles/roleFormat'
import { formatMoney } from '../payroll/payslipFormat'

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const inputClass =
  'border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition w-full'

function Field({ label, value, testId }) {
  return (
    <div>
      <p className="text-xs text-[#71717A] mb-1">{label}</p>
      <p className="text-sm text-[#14142B] font-medium break-words" data-testid={testId}>{value || '—'}</p>
    </div>
  )
}

function PersonLink({ person }) {
  return (
    <Link to={`/organization/employees/${person.id}`} className="text-[#6C31D6] hover:underline">
      {personName(person.full_name, person.user_email)}
    </Link>
  )
}

function EmployeeDetailPage() {
  const { id } = useParams()
  const { hasPermission } = useAuth()
  const canAssignRoles = hasPermission('assign_roles')
  const canManageEmployees = hasPermission('manage_employees')

  const [employee, setEmployee] = useState(null)
  const [access, setAccess] = useState(null)        // null: this person may not see it
  const [assignments, setAssignments] = useState([])
  const [roles, setRoles] = useState([])
  const [selectedRole, setSelectedRole] = useState('')
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [fieldErrors, setFieldErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState('')

  const load = useCallback(async () => {
    try {
      const emp = await getEmployee(id)
      setEmployee(emp)
      setNotFound(false)
      const accessData = await getEmployeeAccess(id).catch(() => null)
      setAccess(accessData)
      if (canAssignRoles) {
        const [empRoles, roleList] = await Promise.all([getEmployeeRoles(), getRoles()])
        setAssignments(empRoles.filter((a) => a.employee === id))
        setRoles(roleList)
      }
    } catch (err) {
      if (err.response?.status === 404) setNotFound(true)
      else setError('Failed to load employee.')
    } finally {
      setLoading(false)
    }
  }, [id, canAssignRoles])

  useEffect(() => {
    Promise.resolve().then(load)
  }, [load])

  async function handleAssign(e) {
    e.preventDefault()
    if (!selectedRole) return
    setError('')
    try {
      await assignEmployeeRole(id, selectedRole)
      setSelectedRole('')
      load()
    } catch (err) {
      setError(errorMessage(err, 'Failed to assign role. The employee may already have it.'))
    }
  }

  async function handleRevoke(assignmentId) {
    if (!confirm('Revoke this role from the employee?')) return
    setError('')
    try {
      await deleteEmployeeRole(assignmentId)
      load()
    } catch (err) {
      setError(errorMessage(err, 'Failed to revoke role.'))
    }
  }

  function startEdit() {
    setForm({
      phone: employee.phone || '',
      address: employee.address || '',
      emergency_contact_name: employee.emergency_contact_name || '',
      emergency_contact_phone: employee.emergency_contact_phone || '',
      joined_on: employee.joined_on || '',
    })
    setFieldErrors({})
    setSaved('')
    setError('')
    setEditing(true)
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setFieldErrors({})
    setError('')
    try {
      await updateEmployee(id, { ...form, joined_on: form.joined_on || null })
      setEditing(false)
      setSaved('Details saved.')
      await load()
    } catch (err) {
      setFieldErrors(err.response?.data?.error?.field_errors || {})
      setError(errorMessage(err, 'Could not save the details.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <p className="text-sm text-[#71717A]">Loading...</p>

  if (notFound) {
    return (
      <div>
        <Link to="/organization/employees" className="inline-flex items-center gap-1 text-sm text-[#6C31D6] hover:underline mb-4">
          <ArrowLeft size={14} /> Back to employees
        </Link>
        <p className="text-sm text-[#71717A]">Employee not found.</p>
      </div>
    )
  }
  if (!employee) return error ? <p className="text-sm text-[#DC2626]">{error}</p> : null

  const manager = (employee.managers || [])[0]
  const chain = [...(employee.managers || [])].reverse()   // from the top down to the direct manager
  const assignedRoleIds = new Set(assignments.map((a) => a.role))
  const assignableRoles = roles.filter((r) => !assignedRoleIds.has(r.id))
  const assignmentByRole = Object.fromEntries(assignments.map((a) => [a.role, a]))

  return (
    <div className="pb-12 max-w-4xl">
      <Link to="/organization/employees" className="inline-flex items-center gap-1 text-sm text-[#6C31D6] hover:underline mb-4">
        <ArrowLeft size={14} /> Back to employees
      </Link>

      <h1 className="text-2xl font-bold text-[#14142B]" data-testid="employee-name">
        {personName(employee.full_name, employee.user_email)}
      </h1>
      <p className="text-sm text-[#71717A] mt-1 mb-6">
        {[employee.designation_title, employee.department_name].filter(Boolean).join(' · ') || 'No designation yet'}
      </p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}
      {saved && <p className="text-sm text-green-700 mb-4">{saved}</p>}

      {/* ---- Profile ---- */}
      <div className="bg-white rounded-xl border border-[#EEEEF2] p-5 mb-6" data-testid="profile-section">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-[#14142B]">Profile</h2>
          {canManageEmployees && employee.contact_visible && !editing && (
            <button onClick={startEdit} data-testid="edit-details" className="flex items-center gap-1.5 border border-[#EEEEF2] hover:bg-[#FAFAFA] rounded-lg px-3 py-1.5 text-sm text-[#14142B] transition">
              <Pencil size={14} /> Edit details
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Field label="Designation" value={employee.designation_title} />
          <Field label="Department" value={employee.department_name} />
          <div>
            <p className="text-xs text-[#71717A] mb-1">Reports to</p>
            <p className="text-sm font-medium">{manager ? <PersonLink person={manager} /> : '—'}</p>
          </div>
          {employee.contact_visible && (
            <>
              <Field label="Email" value={employee.user_email} testId="detail-email" />
              <Field label="Employee code" value={employee.employee_code} />
              <Field label="Joined on" value={employee.joined_on} testId="detail-joined" />
            </>
          )}
        </div>

        {employee.contact_visible ? (
          editing ? (
            <form onSubmit={handleSave} className="mt-5 pt-5 border-t border-[#EEEEF2]" noValidate>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  ['phone', 'Phone', 'text'],
                  ['address', 'Address', 'text'],
                  ['emergency_contact_name', 'Emergency contact name', 'text'],
                  ['emergency_contact_phone', 'Emergency contact phone', 'text'],
                  ['joined_on', 'Joined on', 'date'],
                ].map(([key, label, type]) => (
                  <div key={key}>
                    <label htmlFor={`d-${key}`} className="block text-xs text-[#71717A] mb-1">{label}</label>
                    <input
                      id={`d-${key}`} type={type} value={form[key]}
                      onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                      className={`${inputClass} ${fieldErrors[key] ? 'border-red-400' : ''}`}
                    />
                    {fieldErrors[key] && <p className="text-xs text-red-600 mt-1">{fieldErrors[key]}</p>}
                  </div>
                ))}
              </div>
              <div className="flex gap-2 mt-4">
                <button type="submit" disabled={saving} data-testid="save-details" className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 text-white rounded-lg px-5 py-2 text-sm font-medium transition">
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button type="button" onClick={() => setEditing(false)} className="border border-[#EEEEF2] rounded-lg px-5 py-2 text-sm text-[#14142B]">Cancel</button>
              </div>
            </form>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5 pt-5 border-t border-[#EEEEF2]" data-testid="contact-section">
              <Field label="Phone" value={employee.phone} testId="detail-phone" />
              <Field label="Address" value={employee.address} testId="detail-address" />
              <Field label="Emergency contact" value={employee.emergency_contact_name} />
              <Field label="Emergency contact phone" value={employee.emergency_contact_phone} />
            </div>
          )
        ) : (
          <p className="mt-5 pt-4 border-t border-[#EEEEF2] flex items-start gap-2 text-xs text-[#71717A]" data-testid="contact-private-note">
            <Lock size={14} className="mt-0.5 shrink-0" />
            Contact details are private: only this person, their managers and HR can see them.
          </p>
        )}
      </div>

      {/* ---- Reporting line ---- */}
      <div className="bg-white rounded-xl border border-[#EEEEF2] p-5 mb-6" data-testid="hierarchy-section">
        <h2 className="text-base font-semibold text-[#14142B] mb-3">Reporting line</h2>
        <p className="text-xs text-[#71717A] mb-1">Managers above</p>
        {chain.length === 0 ? (
          <p className="text-sm text-[#A1A1AA] italic mb-4">At the top: reports to no one.</p>
        ) : (
          <p className="text-sm mb-4 flex flex-wrap items-center gap-1.5">
            {chain.map((m) => (
              <span key={m.id} className="flex items-center gap-1.5">
                <PersonLink person={m} /> <span className="text-[#A1A1AA]">›</span>
              </span>
            ))}
            <span className="font-medium text-[#14142B]">{personName(employee.full_name, employee.user_email)}</span>
          </p>
        )}
        <p className="text-xs text-[#71717A] mb-1">Direct reports</p>
        {(employee.direct_reports || []).length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-[#A1A1AA]"><Users size={16} /> No one reports to this person.</div>
        ) : (
          <ul className="divide-y divide-[#EEEEF2]">
            {employee.direct_reports.map((r) => (
              <li key={r.id} className="py-2 flex items-center justify-between text-sm">
                <span><PersonLink person={r} /> <span className="text-xs text-[#71717A]">· {r.employee_code}</span></span>
                <span className="text-xs text-[#71717A]">{r.designation_title || '—'}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ---- Roles and Permissions: only for people who may see them ---- */}
      {access && (
        <div className="bg-white rounded-xl border border-[#EEEEF2] p-5 mb-6" data-testid="permissions-section">
          <h2 className="text-base font-semibold text-[#14142B] mb-1 flex items-center gap-2"><Shield size={16} className="text-[#6C31D6]" /> Roles and Permissions</h2>
          <p className="text-xs text-[#71717A] mb-4">What this person can really do, through the Roles they hold.</p>

          {access.roles.length === 0 ? (
            <p className="text-sm text-[#71717A] mb-4" data-testid="no-permissions">No Permissions. This person holds no Role yet.</p>
          ) : (
            access.roles.map((role) => (
              <div key={role.id} className="mb-5" data-testid="role-block">
                <div className="flex items-center gap-2 mb-2">
                  <Link to={`/roles/${role.id}`} className="text-sm font-semibold text-[#14142B] hover:text-[#6C31D6]">{role.name}</Link>
                  {role.is_system_default && <span className="text-[10px] bg-[#6C31D6]/10 text-[#6C31D6] px-1.5 py-0.5 rounded font-medium">System</span>}
                  {canAssignRoles && assignmentByRole[role.id] && (
                    <button onClick={() => handleRevoke(assignmentByRole[role.id].id)} title="Revoke role" className="text-[#71717A] hover:text-[#DC2626] transition">
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
                {role.permissions.length === 0 ? (
                  <p className="text-xs text-[#A1A1AA] italic ml-1">No Permissions</p>
                ) : (
                  groupByModule(role.permissions).map(([module, perms]) => (
                    <div key={module} className="mb-2 ml-1">
                      <p className="text-[10px] uppercase tracking-wide text-[#A1A1AA] mb-1">{moduleLabel(module)}</p>
                      <ul className="space-y-1">
                        {perms.map((p) => (
                          <li key={p.codename} className="text-sm">
                            <span className="font-medium text-[#14142B]">{p.name}</span>
                            <span className="text-xs text-[#71717A]"> — {p.description}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))
                )}
              </div>
            ))
          )}

          {canAssignRoles && (
            <form onSubmit={handleAssign} className="flex flex-wrap items-center gap-3 pt-4 border-t border-[#EEEEF2]">
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] bg-white min-w-[200px]"
                required
              >
                <option value="">Role...</option>
                {assignableRoles.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
              <button type="submit" className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-5 py-2 text-sm font-medium transition-all duration-150">
                <UserPlus size={16} /> Assign
              </button>
            </form>
          )}
        </div>
      )}

      {/* ---- Salary: manage_finance only ---- */}
      {employee.salary !== undefined && (
        <div className="bg-white rounded-xl border border-[#EEEEF2] p-5" data-testid="salary-section">
          <h2 className="text-base font-semibold text-[#14142B] mb-3">Salary and payroll</h2>
          {employee.salary === null ? (
            <p className="text-sm text-[#A1A1AA] italic">No salary structure yet.</p>
          ) : (
            <div className="text-sm space-y-1 mb-4">
              <p>Base salary: <span className="font-medium">{formatMoney(employee.salary.base_salary)}</span></p>
              {Object.entries(employee.salary.allowances || {}).map(([name, amount]) => (
                <p key={name} className="text-[#71717A]">{name}: {formatMoney(amount)}</p>
              ))}
            </div>
          )}
          {(employee.recent_payslips || []).length > 0 && (
            <ul className="divide-y divide-[#EEEEF2]">
              {employee.recent_payslips.map((p) => (
                <li key={p.id} className="py-2 flex justify-between text-sm">
                  <Link to={`/payroll/payslips/${p.id}`} className="text-[#6C31D6] hover:underline">{MONTHS[p.month - 1]} {p.year}</Link>
                  <span>{formatMoney(p.net_amount)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default EmployeeDetailPage
