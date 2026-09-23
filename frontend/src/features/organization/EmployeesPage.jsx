import { useEffect, useState } from 'react'
import { Users } from 'lucide-react'
import { getEmployees } from '../../services/organizationService'

function EmployeesPage() {
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const data = await getEmployees()
        setEmployees(data)
      } catch (err) {
        setError('Failed to load employees.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold text-[#14142B]">Employees</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-6">Everyone in your company.</p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : employees.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-14 flex flex-col items-center text-center">
          <Users className="text-[#71717A]/40 mb-3" size={36} />
          <p className="text-sm text-[#71717A]">No employees yet.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#FAFAFA] text-[#71717A] text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Employee</th>
                <th className="px-4 py-3 font-medium">Designation</th>
                <th className="px-4 py-3 font-medium">Department</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEEEF2]">
              {employees.map((emp) => (
                <tr key={emp.id} className="text-[#14142B] hover:bg-[#FAFAFA] transition-colors duration-150">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-[#6C31D6]/10 text-[#6C31D6] flex items-center justify-center text-xs font-semibold shrink-0">
                        {emp.employee_code?.slice(-2) || '??'}
                      </div>
                      <span className="font-medium">{emp.employee_code}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[#71717A]">{emp.designation_title || '—'}</td>
                  <td className="px-4 py-3 text-[#71717A]">{emp.department_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default EmployeesPage