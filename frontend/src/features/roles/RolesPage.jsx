import { useEffect, useState } from 'react'
import { Shield, Plus, Check, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { getPermissions, getRoles, createRole, deleteRole, updateRole } from '../../services/rolesService'

function RolesPage() {
  const [roles, setRoles] = useState([])
  const [permissions, setPermissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create form
  const [roleName, setRoleName] = useState('')
  const [roleDesc, setRoleDesc] = useState('')
  const [selectedPerms, setSelectedPerms] = useState([])
  const [showForm, setShowForm] = useState(false)

  // Expanded role (to show details)
  const [expandedRole, setExpandedRole] = useState(null)

  async function loadData() {
    setLoading(true)
    try {
      const [rolesData, permsData] = await Promise.all([getRoles(), getPermissions()])
      setRoles(rolesData)
      setPermissions(permsData)
    } catch (err) {
      setError('Failed to load data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Group permissions by module
  const permsByModule = permissions.reduce((acc, perm) => {
    if (!acc[perm.module]) acc[perm.module] = []
    acc[perm.module].push(perm)
    return acc
  }, {})

  function togglePerm(permId) {
    setSelectedPerms((prev) =>
      prev.includes(permId) ? prev.filter((id) => id !== permId) : [...prev, permId]
    )
  }

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    try {
      await createRole({
        name: roleName,
        description: roleDesc,
        permissions: selectedPerms,
      })
      setRoleName('')
      setRoleDesc('')
      setSelectedPerms([])
      setShowForm(false)
      loadData()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to create role.')
    }
  }

  async function handleDelete(id) {
    if (!confirm('Are you sure you want to delete this role?')) return
    try {
      await deleteRole(id)
      loadData()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to delete role.')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#14142B]">Roles</h1>
          <p className="text-sm text-[#71717A] mt-1">
            Create roles and assign permissions to control access.
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
        >
          <Plus size={16} /> New Role
        </button>
      </div>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}

      {/* -------- CREATE ROLE FORM -------- */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-5 mb-6"
        >
          <h2 className="text-base font-semibold text-[#14142B] mb-4">Create New Role</h2>

          <div className="flex gap-3 mb-4">
            <input
              type="text"
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
              placeholder="Role name (e.g. HR Manager)"
              className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition flex-1"
              required
            />
            <input
              type="text"
              value={roleDesc}
              onChange={(e) => setRoleDesc(e.target.value)}
              placeholder="Description (optional)"
              className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition flex-1"
            />
          </div>

          {/* Permissions grouped by module */}
          <div className="mb-4">
            <p className="text-sm font-medium text-[#14142B] mb-2">Select Permissions</p>
            {Object.entries(permsByModule).map(([module, perms]) => (
              <div key={module} className="mb-3">
                <p className="text-xs font-semibold text-[#71717A] uppercase tracking-wider mb-1.5">
                  {module}
                </p>
                <div className="flex flex-wrap gap-2">
                  {perms.map((perm) => {
                    const isSelected = selectedPerms.includes(perm.id)
                    return (
                      <button
                        key={perm.id}
                        type="button"
                        onClick={() => togglePerm(perm.id)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border transition-all duration-150 ${
                          isSelected
                            ? 'bg-[#6C31D6] text-white border-[#6C31D6]'
                            : 'bg-white text-[#14142B] border-[#EEEEF2] hover:border-[#6C31D6]/40'
                        }`}
                      >
                        {isSelected && <Check size={14} />}
                        {perm.name}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
            >
              <Plus size={16} /> Create Role
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm text-[#71717A] hover:text-[#14142B] transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* -------- ROLES LIST -------- */}
      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : roles.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-14 flex flex-col items-center text-center">
          <Shield className="text-[#71717A]/40 mb-3" size={36} />
          <p className="text-sm text-[#71717A]">No roles yet. Create your first one above.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] divide-y divide-[#EEEEF2]">
          {roles.map((role) => (
            <div key={role.id}>
              <div
                className="px-4 py-3 flex items-center justify-between hover:bg-[#FAFAFA] transition-colors duration-150 cursor-pointer"
                onClick={() => setExpandedRole(expandedRole === role.id ? null : role.id)}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[#6C31D6]/10 text-[#6C31D6] flex items-center justify-center shrink-0">
                    <Shield size={16} />
                  </div>
                  <div>
                    <span className="text-sm text-[#14142B] font-medium">{role.name}</span>
                    {role.is_system_default && (
                      <span className="ml-2 text-xs bg-[#6C31D6]/10 text-[#6C31D6] px-2 py-0.5 rounded-full">
                        System
                      </span>
                    )}
                    {role.description && (
                      <p className="text-xs text-[#71717A] mt-0.5">{role.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#71717A]">
                    {role.permission_details?.length || 0} permissions
                  </span>
                  {!role.is_system_default && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(role.id)
                      }}
                      className="p-1.5 text-[#71717A] hover:text-[#DC2626] hover:bg-[#DC2626]/10 rounded-lg transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  )}
                  {expandedRole === role.id ? (
                    <ChevronUp size={16} className="text-[#71717A]" />
                  ) : (
                    <ChevronDown size={16} className="text-[#71717A]" />
                  )}
                </div>
              </div>

              {/* Expanded: show permissions */}
              {expandedRole === role.id && (
                <div className="px-4 pb-3 pt-1">
                  <div className="flex flex-wrap gap-1.5">
                    {role.permission_details?.length > 0 ? (
                      role.permission_details.map((perm) => (
                        <span
                          key={perm.id}
                          className="text-xs bg-[#F1EEFB] text-[#6C31D6] px-2.5 py-1 rounded-lg"
                        >
                          {perm.name}
                        </span>
                      ))
                    ) : (
                      <p className="text-xs text-[#71717A]">No permissions assigned.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default RolesPage
