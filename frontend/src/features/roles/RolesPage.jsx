import { useEffect, useState } from 'react'
import { Plus, Shield, Trash2, UserPlus } from 'lucide-react'
import { getPermissions, getRoles, createRole, deleteRole } from '../../services/rolesService'
import { getEmployees, getEmployeeRoles, assignEmployeeRole, deleteEmployeeRole } from '../../services/organizationService'

// All standard system permissions from design
const DEFAULT_PERMISSION_CODENAMES = [
  'approve_leave',
  'manage_departments',
  'manage_employees',
  'manage_roles',
  'manage_approval_chains',
  'approve_request',
  'create_task',
  'manage_attendance',
  'manage_payroll',
  'view_finance',
  'approve_expense',
  'approve_support_access',
]

function RolesPage() {
  const [roles, setRoles] = useState([])
  const [permissions, setPermissions] = useState([])
  const [employees, setEmployees] = useState([])
  const [employeeRoles, setEmployeeRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Create Role Form state
  const [roleName, setRoleName] = useState('')
  const [selectedPerms, setSelectedPerms] = useState([])

  // Assign Role Form state
  const [selectedEmployee, setSelectedEmployee] = useState('')
  const [selectedRole, setSelectedRole] = useState('')

  async function loadData() {
    setLoading(true)
    setError('')
    try {
      const [rolesData, permsData, empsData, empRolesData] = await Promise.all([
        getRoles().catch(() => []),
        getPermissions().catch(() => []),
        getEmployees().catch(() => []),
        getEmployeeRoles().catch(() => []),
      ])

      setRoles(rolesData || [])
      setEmployees(empsData || [])
      setEmployeeRoles(empRolesData || [])

      // Merge backend permissions with standard list to ensure all 12 are available
      const backendPerms = permsData || []
      const merged = DEFAULT_PERMISSION_CODENAMES.map((codename) => {
        const found = backendPerms.find((p) => p.codename === codename)
        return found || { id: codename, codename, name: codename }
      })
      // Add any additional backend permissions not in the default list
      backendPerms.forEach((bp) => {
        if (!merged.some((m) => m.codename === bp.codename)) {
          merged.push(bp)
        }
      })
      setPermissions(merged)
    } catch (err) {
      setError('Failed to load roles and permissions.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  function togglePerm(idOrCodename) {
    setSelectedPerms((prev) =>
      prev.includes(idOrCodename)
        ? prev.filter((item) => item !== idOrCodename)
        : [...prev, idOrCodename]
    )
  }

  async function handleCreateRole(e) {
    e.preventDefault()
    if (!roleName.trim()) return
    setError('')
    setSuccess('')

    // Map selected permissions to backend IDs where possible
    const permIds = selectedPerms
      .map((item) => {
        const match = permissions.find((p) => p.id === item || p.codename === item)
        return match ? match.id : item
      })
      .filter((id) => typeof id === 'string' && id.includes('-')) // only valid UUIDs if applicable

    try {
      await createRole({
        name: roleName.trim(),
        permissions: permIds,
      })
      setRoleName('')
      setSelectedPerms([])
      setSuccess(`Role "${roleName.trim()}" created successfully!`)
      loadData()
    } catch (err) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to create role.')
    }
  }

  async function handleDeleteRole(roleId) {
    if (!confirm('Are you sure you want to delete this role?')) return
    setError('')
    setSuccess('')
    try {
      await deleteRole(roleId)
      setSuccess('Role deleted.')
      loadData()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to delete role.')
    }
  }

  async function handleAssignRole(e) {
    e.preventDefault()
    if (!selectedEmployee || !selectedRole) {
      setError('Please select both an employee and a role.')
      return
    }
    setError('')
    setSuccess('')

    try {
      await assignEmployeeRole(selectedEmployee, selectedRole)
      setSuccess('Role assigned to employee successfully!')
      setSelectedRole('')
      loadData()
    } catch (err) {
      const data = err.response?.data
      const message =
        data?.error?.message ||
        data?.non_field_errors?.[0] ||
        data?.detail ||
        (typeof data === 'string' ? data : null) ||
        'Failed to assign role. The employee might already have this role.'
      setError(message)
    }
  }

  async function handleRevokeRole(assignmentId) {
    if (!confirm('Revoke this role assignment?')) return
    setError('')
    setSuccess('')
    try {
      await deleteEmployeeRole(assignmentId)
      setSuccess('Role revoked.')
      loadData()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to revoke role.')
    }
  }

  return (
    <div className="pb-12">
      {/* Header */}
      <h1 className="text-2xl font-bold text-[#14142B]">Roles & Permissions</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-6">
        Define roles and assign them to employees.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
          {success}
        </div>
      )}

      {/* ---------------- 1. CREATE A ROLE ---------------- */}
      <div className="bg-white rounded-xl border border-[#EEEEF2] p-6 mb-8">
        <h2 className="text-base font-semibold text-[#14142B] mb-4">Create a Role</h2>

        <form onSubmit={handleCreateRole}>
          <input
            type="text"
            value={roleName}
            onChange={(e) => setRoleName(e.target.value)}
            placeholder="Role name (e.g. Department Manager)"
            className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition w-full max-w-sm mb-4"
            required
          />

          {/* 3-column permission checkboxes matching screenshot */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-y-3 gap-x-4 mb-6">
            {permissions.map((perm) => {
              const key = perm.id || perm.codename
              const isChecked = selectedPerms.includes(key)
              return (
                <label
                  key={key}
                  className="flex items-center gap-2.5 text-sm text-[#14142B] cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => togglePerm(key)}
                    className="rounded border-[#D1D5DB] text-[#6C31D6] focus:ring-[#6C31D6] w-4 h-4"
                  />
                  <span className="text-sm font-normal text-[#14142B]">
                    {perm.codename}
                  </span>
                </label>
              )
            })}
          </div>

          <button
            type="submit"
            className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-5 py-2 text-sm font-medium transition-all duration-150"
          >
            <Plus size={16} /> Create Role
          </button>
        </form>
      </div>

      {/* ---------------- 2. EXISTING ROLES ---------------- */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-[#14142B]">Existing Roles</h2>
          <span className="text-xs text-[#71717A]">{roles.length} total</span>
        </div>

        {roles.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-8 text-center text-sm text-[#71717A]">
            No roles created yet. Use the form above to create your first role.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {roles.map((r) => (
              <div
                key={r.id}
                className="bg-white rounded-xl border border-[#EEEEF2] p-4 shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Shield size={16} className="text-[#6C31D6]" />
                      <span className="text-sm font-bold text-[#14142B]">{r.name}</span>
                      {r.is_system_default && (
                        <span className="text-[10px] bg-[#6C31D6]/10 text-[#6C31D6] px-1.5 py-0.5 rounded font-medium">
                          System
                        </span>
                      )}
                    </div>
                    {!r.is_system_default && (
                      <button
                        onClick={() => handleDeleteRole(r.id)}
                        title="Delete Role"
                        className="text-[#71717A] hover:text-[#DC2626] transition p-1"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                  {r.description && (
                    <p className="text-xs text-[#71717A] mb-2">{r.description}</p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {r.permission_details && r.permission_details.length > 0 ? (
                      r.permission_details.map((p) => (
                        <span
                          key={p.id}
                          className="text-[11px] font-mono bg-[#F1EEFB] text-[#6C31D6] px-2 py-0.5 rounded"
                        >
                          {p.codename}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-[#A1A1AA] italic">No permissions assigned</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ---------------- 3. ASSIGN ROLE TO EMPLOYEE ---------------- */}
      <div className="mb-8">
        <h2 className="text-base font-semibold text-[#14142B] mb-3">
          Assign Role to Employee
        </h2>

        <form onSubmit={handleAssignRole} className="flex flex-wrap items-center gap-3">
          {/* Employee Dropdown */}
          <select
            value={selectedEmployee}
            onChange={(e) => setSelectedEmployee(e.target.value)}
            className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] bg-white min-w-[220px]"
            required
          >
            <option value="">Employee...</option>
            {employees.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.employee_code} {emp.email || emp.user?.email ? `— ${emp.email || emp.user?.email}` : ''}
              </option>
            ))}
          </select>

          {/* Role Dropdown */}
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] bg-white min-w-[180px]"
            required
          >
            <option value="">Role...</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          {/* Assign Button */}
          <button
            type="submit"
            className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-5 py-2 text-sm font-medium transition-all duration-150"
          >
            <UserPlus size={16} /> Assign
          </button>
        </form>
      </div>

      {/* ---------------- 4. EMPLOYEE → ROLE ASSIGNMENTS ---------------- */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-[#14142B]">
            Employee → Role Assignments
          </h2>
          <span className="text-xs text-[#71717A]">
            {employeeRoles.length} assignment{employeeRoles.length === 1 ? '' : 's'}
          </span>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-hidden">
          {loading ? (
            <div className="py-10 text-center text-sm text-[#71717A]">Loading assignments...</div>
          ) : employeeRoles.length === 0 ? (
            <div className="py-10 text-center text-sm text-[#71717A]">
              No role assignments yet. Select an employee and role above to assign.
            </div>
          ) : (
            <div className="divide-y divide-[#EEEEF2]">
              {employeeRoles.map((item) => (
                <div
                  key={item.id}
                  className="px-6 py-3.5 flex items-center justify-between hover:bg-[#FAFAFA] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-sm text-[#14142B]">
                      {item.employee_code || item.employee}
                    </span>
                    {item.employee_email && (
                      <span className="text-xs text-[#71717A]">({item.employee_email})</span>
                    )}
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="inline-block bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE] px-3 py-1 rounded-full text-xs font-medium">
                      {item.role_name || (roles.find((r) => r.id === item.role)?.name ?? 'Role')}
                    </span>
                    <button
                      onClick={() => handleRevokeRole(item.id)}
                      title="Revoke role"
                      className="text-[#71717A] hover:text-[#DC2626] transition p-1"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default RolesPage
