import { useEffect, useState } from 'react'
import { Users, Plus } from 'lucide-react'
import {
  getEmployees,
  createEmployee,
  getDepartments,
  getDesignations,
} from '../../services/organizationService'
import { useAuth } from '../../store/AuthContext'

function EmployeesPage() {
  const [employees, setEmployees] = useState([])
  const [departments, setDepartments] = useState([])
  const [designations, setDesignations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    email: '',
    password: '',
    employee_code: '',
    department: '',
    designation: '',
    reports_to: '',
  })

  const { hasPermission } = useAuth()
  const canManageEmployees = hasPermission('manage_employees')

  async function loadAll() {
    setLoading(true)


    try {
      const [emps, depts, desigs] = await Promise.all([
        getEmployees(),
        getDepartments(),
        getDesignations(),
      ])

      setEmployees(emps)
      setDepartments(depts)
      setDesignations(desigs)
    } catch (err) {
      setError('Failed to load employees.')
    } finally {
      setLoading(false)
    }

  }

  useEffect(() => {
    loadAll()
  }, [])

  function handleChange(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    })
  }

  async function handleCreate(e) {
    e.preventDefault()
    setError('')


    try {
      await createEmployee({
        email: form.email,
        password: form.password,
        employee_code: form.employee_code,
        department: form.department || null,
        designation: form.designation || null,
        reports_to: form.reports_to || null,
      })

      setForm({
        email: '',
        password: '',
        employee_code: '',
        department: '',
        designation: '',
        reports_to: '',
      })

      loadAll()
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
        'Failed to create employee.'
      )
    }


  }

  return (<div> <h1 className="text-2xl font-bold text-[#14142B]">
    Employees </h1>


    <p className="text-sm text-[#71717A] mt-1 mb-6">
      Everyone in your company.
    </p>

    {canManageEmployees && (
      <form
        onSubmit={handleCreate}
        className="bg-white rounded-xl border border-[#EEEEF2] p-4 mb-6 grid grid-cols-2 md:grid-cols-3 gap-3"
      >
        <input
          type="email"
          name="email"
          value={form.email}
          onChange={handleChange}
          placeholder="Email"
          required
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition"
        />

        <input
          type="password"
          name="password"
          value={form.password}
          onChange={handleChange}
          placeholder="Password"
          required
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition"
        />

        <input
          type="text"
          name="employee_code"
          value={form.employee_code}
          onChange={handleChange}
          placeholder="Employee code"
          required
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition"
        />

        <select
          name="department"
          value={form.department}
          onChange={handleChange}
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] transition"
        >
          <option value="">Department (optional)</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>

        <select
          name="designation"
          value={form.designation}
          onChange={handleChange}
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] transition"
        >
          <option value="">Designation (optional)</option>
          {designations.map((d) => (
            <option key={d.id} value={d.id}>
              {d.title}
            </option>
          ))}
        </select>

        <select
          name="reports_to"
          value={form.reports_to}
          onChange={handleChange}
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] transition"
        >
          <option value="">Reports To (optional)</option>
          {employees.map((emp) => (
            <option key={emp.id} value={emp.id}>
              {emp.employee_code}
            </option>
          ))}
        </select>

        <button
          type="submit"
          className="col-span-2 md:col-span-3 flex items-center justify-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
        >
          <Plus size={16} />
          Add Employee
        </button>
      </form>
    )}

    {error && (
      <p className="text-sm text-[#DC2626] mb-4">
        {error}
      </p>
    )}

    {loading ? (
      <p className="text-sm text-[#71717A]">
        Loading...
      </p>
    ) : employees.length === 0 ? (
      <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-14 flex flex-col items-center text-center">
        <Users
          className="text-[#71717A]/40 mb-3"
          size={36}
        />

        <p className="text-sm text-[#71717A]">
          No employees yet. Add your first one above.
        </p>
      </div>
    ) : (
      <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#FAFAFA] text-[#71717A] text-left">
            <tr>
              <th className="px-4 py-3 font-medium">
                Employee
              </th>
              <th className="px-4 py-3 font-medium">
                Designation
              </th>
              <th className="px-4 py-3 font-medium">
                Department
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-[#EEEEF2]">
            {employees.map((emp) => (
              <tr
                key={emp.id}
                className="text-[#14142B] hover:bg-[#FAFAFA] transition-colors duration-150"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-[#6C31D6]/10 text-[#6C31D6] flex items-center justify-center text-xs font-semibold shrink-0">
                      {emp.employee_code?.slice(-2) || '??'}
                    </div>

                    <span className="font-medium">
                      {emp.employee_code}
                    </span>
                  </div>
                </td>

                <td className="px-4 py-3 text-[#71717A]">
                  {emp.designation_title || '—'}
                </td>

                <td className="px-4 py-3 text-[#71717A]">
                  {emp.department_name || '—'}
                </td>
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
