import { useState } from 'react'
import { UserPlus, Trash2, Shield } from 'lucide-react'

function EmployeeRolesPage() {
  const [employee, setEmployee] = useState('')
  const [role, setRole] = useState('')

  // Temporary demo data — API connect করার সময় এগুলো backend থেকে আসবে
  const employees = [
    { id: '1', employee_code: 'EMP-001', email: 'employee1@example.com' },
    { id: '2', employee_code: 'EMP-002', email: 'employee2@example.com' },
  ]

  const roles = [
    { id: '1', name: 'Admin' },
    { id: '2', name: 'HR Manager' },
    { id: '3', name: 'Employee' },
  ]

  const assignedRoles = [
    {
      id: '1',
      employee_code: 'EMP-001',
      employee_email: 'employee1@example.com',
      role_name: 'Admin',
    },
  ]

  function handleAssign(e) {
    e.preventDefault()
    console.log('Assign:', { employee, role })
  }

  function handleRevoke(id) {
    console.log('Revoke:', id)
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#14142B]">
          Employee Roles
        </h1>
        <p className="text-sm text-[#71717A] mt-1">
          Assign and revoke roles for employees in your company.
        </p>
      </div>

      {/* Assign Role Form */}
      <form
        onSubmit={handleAssign}
        className="bg-white rounded-xl border border-[#EEEEF2] p-5 mb-6"
      >
        <div className="flex items-center gap-2 mb-4">
          <UserPlus size={18} className="text-[#6C31D6]" />
          <h2 className="text-base font-semibold text-[#14142B]">
            Assign Role
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Employee */}
          <select
            value={employee}
            onChange={(e) => setEmployee(e.target.value)}
            className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] transition"
            required
          >
            <option value="">Select Employee</option>
            {employees.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.employee_code} — {emp.email}
              </option>
            ))}
          </select>

          {/* Role */}
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] transition"
            required
          >
            <option value="">Select Role</option>
            {roles.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>

          {/* Button */}
          <button
            type="submit"
            className="flex items-center justify-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all"
          >
            <UserPlus size={16} />
            Assign Role
          </button>
        </div>
      </form>

      {/* Assigned Roles */}
      <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-hidden">
        <div className="px-4 py-4 border-b border-[#EEEEF2] flex items-center gap-2">
          <Shield size={18} className="text-[#6C31D6]" />
          <h2 className="text-base font-semibold text-[#14142B]">
            Assigned Roles
          </h2>
        </div>

        {assignedRoles.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm text-[#71717A]">
              No roles assigned yet.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-[#FAFAFA] text-[#71717A] text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Employee</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium text-right">
                  Action
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#EEEEF2]">
              {assignedRoles.map((item) => (
                <tr
                  key={item.id}
                  className="text-[#14142B] hover:bg-[#FAFAFA] transition-colors"
                >
                  <td className="px-4 py-3 font-medium">
                    {item.employee_code}
                  </td>

                  <td className="px-4 py-3 text-[#71717A]">
                    {item.employee_email}
                  </td>

                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-1 bg-[#F1EEFB] text-[#6C31D6] px-2.5 py-1 rounded-lg text-xs font-medium">
                      <Shield size={13} />
                      {item.role_name}
                    </span>
                  </td>

                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRevoke(item.id)}
                      className="inline-flex items-center gap-1.5 text-[#DC2626] hover:bg-[#DC2626]/10 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
                    >
                      <Trash2 size={14} />
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default EmployeeRolesPage