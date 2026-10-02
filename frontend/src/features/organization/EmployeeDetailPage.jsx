import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Trash2, UserPlus, Users } from 'lucide-react'
import {
  getEmployee,
  getEmployees,
  getSubordinates,
  getEmployeeRoles,
  assignEmployeeRole,
  deleteEmployeeRole,
} from '../../services/organizationService'
import { getRoles } from '../../services/rolesService'
import { useAuth } from '../../store/AuthContext'

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

function EmployeeDetailPage() {
  const { id } = useParams()
  const { hasPermission } = useAuth()
  const canAssignRoles = hasPermission('assign_roles')

  const [employee, setEmployee] = useState(null)
  const [allEmployees, setAllEmployees] = useState([])
  const [team, setTeam] = useState([])
  const [assignments, setAssignments] = useState([])
  const [roles, setRoles] = useState([])
  const [selectedRole, setSelectedRole] = useState('')
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const [emp, emps, subs, empRoles, roleList] = await Promise.all([
        getEmployee(id),
        getEmployees(),
        getSubordinates(id),
        getEmployeeRoles(),
        getRoles(),
      ])
      setEmployee(emp)
      setAllEmployees(emps)
      setTeam(subs)
      setAssignments(empRoles.filter((a) => a.employee === id))
      setRoles(roleList)
      setNotFound(false)
    } catch (err) {
      if (err.response?.status === 404) setNotFound(true)
      else setError('Failed to load employee.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    setLoading(true)
    load()
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

  const manager = allEmployees.find((e) => e.id === employee?.reports_to)
  const assignedRoleIds = new Set(assignments.map((a) => a.role))
  const assignableRoles = roles.filter((r) => !assignedRoleIds.has(r.id))

  return (
    <div className="pb-12">
      <Link to="/organization/employees" className="inline-flex items-center gap-1 text-sm text-[#6C31D6] hover:underline mb-4">
        <ArrowLeft size={14} /> Back to employees
      </Link>

      <h1 className="text-2xl font-bold text-[#14142B]">{employee.employee_code}</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-6">Employee details, team, and roles.</p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}

      <div className="bg-white rounded-xl border border-[#EEEEF2] p-5 mb-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        <div>
          <p className="text-xs text-[#71717A] mb-1">Designation</p>
          <p className="text-[#14142B] font-medium">{employee.designation_title || '—'}</p>
        </div>
        <div>
          <p className="text-xs text-[#71717A] mb-1">Department</p>
          <p className="text-[#14142B] font-medium">{employee.department_name || '—'}</p>
        </div>
        <div>
          <p className="text-xs text-[#71717A] mb-1">Reports to</p>
          {manager ? (
            <Link to={`/organization/employees/${manager.id}`} className="text-[#6C31D6] font-medium hover:underline">
              {manager.employee_code}
            </Link>
          ) : (
            <p className="text-[#14142B] font-medium">—</p>
          )}
        </div>
      </div>

      <h2 className="text-base font-semibold text-[#14142B] mb-3">
        Team <span className="text-xs font-normal text-[#71717A]">(everyone under this employee, at any level)</span>
      </h2>
      <div className="bg-white rounded-xl border border-[#EEEEF2] mb-8 overflow-hidden">
        {team.length === 0 ? (
          <div className="py-10 flex flex-col items-center text-center">
            <Users className="text-[#71717A]/40 mb-2" size={30} />
            <p className="text-sm text-[#71717A]">No one reports to this employee.</p>
          </div>
        ) : (
          <div className="divide-y divide-[#EEEEF2]">
            {team.map((member) => (
              <div key={member.id} className="px-5 py-3 flex items-center justify-between hover:bg-[#FAFAFA] transition-colors">
                <Link to={`/organization/employees/${member.id}`} className="text-sm font-medium text-[#14142B] hover:text-[#6C31D6]">
                  {member.employee_code}
                </Link>
                <span className="text-xs text-[#71717A]">
                  {member.designation_title || '—'} · {member.department_name || '—'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <h2 className="text-base font-semibold text-[#14142B] mb-3">Roles</h2>
      <div className="bg-white rounded-xl border border-[#EEEEF2] p-5">
        {assignments.length === 0 ? (
          <p className="text-sm text-[#71717A] mb-4">No roles assigned. This employee has no permissions.</p>
        ) : (
          <div className="flex flex-wrap gap-2 mb-4">
            {assignments.map((a) => (
              <span
                key={a.id}
                className="inline-flex items-center gap-1.5 bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE] px-3 py-1 rounded-full text-xs font-medium"
              >
                {a.role_name}
                {canAssignRoles && (
                  <button onClick={() => handleRevoke(a.id)} title="Revoke role" className="hover:text-[#DC2626] transition">
                    <Trash2 size={12} />
                  </button>
                )}
              </span>
            ))}
          </div>
        )}

        {canAssignRoles && (
          <form onSubmit={handleAssign} className="flex flex-wrap items-center gap-3">
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
            <button
              type="submit"
              className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-5 py-2 text-sm font-medium transition-all duration-150"
            >
              <UserPlus size={16} /> Assign
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

export default EmployeeDetailPage
