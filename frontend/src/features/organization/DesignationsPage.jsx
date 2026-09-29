import { useEffect, useState } from 'react'
import { IdCard, Plus, Pencil, Check, X } from 'lucide-react'
import { getDesignations, createDesignation, updateDesignation } from '../../services/organizationService'
import { useAuth } from '../../store/AuthContext'


function DesignationsPage() {
  const [designations, setDesignations] = useState([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [error, setError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')
  const { hasPermission } = useAuth()

  const canManageDesignations = hasPermission('manage_designations')

  async function loadDesignations() {
    setLoading(true)

    try {
      const data = await getDesignations()
      setDesignations(data)
    } catch (err) {
      setError('Failed to load designations.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDesignations()
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')

    try {
      await createDesignation(title)
      setTitle('')
      loadDesignations()
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
        'Failed to create designation.'
      )
    }
  }

  function startEdit(d) {
    setEditingId(d.id)
    setEditValue(d.title)
  }

  function cancelEdit() {
    setEditingId(null)
    setEditValue('')
  }

  async function saveEdit(id) {
    setError('')
    try {
      await updateDesignation(id, editValue)
      setEditingId(null)
      loadDesignations()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update designation.')
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-[#14142B]">
        Designations
      </h1>

      <p className="text-sm text-[#71717A] mt-1 mb-6">
        Job titles used across your company.
      </p>

      <form
        onSubmit={handleCreate}
        className="flex gap-2 mb-6"
      >
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New designation title"
          className="border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition w-64"
          required
        />

        <button
          type="submit"
          className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
        >
          <Plus size={16} />
          Add
        </button>
      </form>

      {error && (
        <p className="text-sm text-[#DC2626] mb-4">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-[#71717A]">
          Loading...
        </p>
      ) : designations.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-14 flex flex-col items-center text-center">
          <IdCard
            className="text-[#71717A]/40 mb-3"
            size={36}
          />

          <p className="text-sm text-[#71717A]">
            No designations yet. Add your first one above.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] divide-y divide-[#EEEEF2]">
          {designations.map((d) => (
            <div
              key={d.id}
              className="px-4 py-3 flex items-center gap-3 hover:bg-[#FAFAFA] transition-colors duration-150"
            >
              <div className="w-8 h-8 rounded-lg bg-[#3B82F6]/10 text-[#3B82F6] flex items-center justify-center shrink-0">
                <IdCard size={16} />
              </div>
              {editingId === d.id ? (
                <>
                  <input
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="flex-1 border border-[#6C31D6]/40 rounded-lg px-2 py-1 text-sm outline-none focus:border-[#6C31D6]"
                    autoFocus
                  />
                  <button onClick={() => saveEdit(d.id)} className="text-[#16A34A] hover:opacity-70 transition">
                    <Check size={18} />
                  </button>
                  <button onClick={cancelEdit} className="text-[#71717A] hover:opacity-70 transition">
                    <X size={18} />
                  </button>
                </>
              ) : (
                <>
                  <span className="flex-1 text-sm text-[#14142B] font-medium">{d.title}</span>
                  <button onClick={() => startEdit(d)} className="text-[#71717A] hover:text-[#6C31D6] transition">
                    <Pencil size={15} />
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default DesignationsPage