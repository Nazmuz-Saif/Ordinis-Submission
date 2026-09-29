import { useEffect, useState } from 'react'
import { Building2, Plus } from 'lucide-react'
import { getDepartments, createDepartment } from '../../services/organizationService'
import { useAuth } from '../../store/AuthContext'

function DepartmentsPage() {
  const { hasPermission } = useAuth()
  const canManageDepartments = hasPermission('manage_departments')

  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  async function loadDepartments() {
    setLoading(true)
    try {
      const data = await getDepartments()
      setDepartments(data)
    } catch (err) {
      setError('Failed to load departments.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDepartments()
  }, [])

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
          <p className="text-sm text-[#71717A]">No departments yet. Add your first one above.</p>
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
              <span className="text-sm text-[#14142B] font-medium">{dept.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DepartmentsPage