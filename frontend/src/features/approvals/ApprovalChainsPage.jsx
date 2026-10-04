import { useEffect, useState } from 'react'
import { ArrowDown, ArrowUp, GitBranch, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getRoles } from '../../services/rolesService'
import {
  getChains, createChain, updateChain, deleteChain,
  reorderChain, createStep, deleteStep,
} from '../../services/approvalsService'

const MODULES = [{ value: 'leave', label: 'Leave Request' }]
const moduleLabel = (value) => MODULES.find((m) => m.value === value)?.label || value

const inputClass =
  'border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition'

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

function ApprovalChainsPage() {
  const { hasPermission } = useAuth()
  const canManage = hasPermission('manage_approval_chains')

  const [chains, setChains] = useState([])
  const [roles, setRoles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [newName, setNewName] = useState('')
  const [newModule, setNewModule] = useState('leave')

  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editModule, setEditModule] = useState('leave')

  // chain id -> role id chosen in that chain's "add step" dropdown
  const [stepRole, setStepRole] = useState({})

  async function loadData() {
    try {
      const [chainData, roleData] = await Promise.all([getChains(), getRoles()])
      setChains(chainData)
      setRoles(roleData)
    } catch (err) {
      setError(errorMessage(err, 'Failed to load approval chains.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([getChains(), getRoles()])
      .then(([chainData, roleData]) => {
        if (!active) return
        setChains(chainData)
        setRoles(roleData)
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, 'Failed to load approval chains.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  async function run(action, successText, failText) {
    setError('')
    setMessage('')
    try {
      await action()
      setMessage(successText)
      await loadData()
    } catch (err) {
      setError(errorMessage(err, failText))
    }
  }

  function handleCreateChain(e) {
    e.preventDefault()
    run(async () => {
      await createChain({ name: newName.trim(), applies_to_module: newModule })
      setNewName('')
    }, 'Approval chain created.', 'Failed to create the chain.')
  }

  function startEdit(chain) {
    setEditingId(chain.id)
    setEditName(chain.name)
    setEditModule(chain.applies_to_module)
  }

  function handleSaveEdit(e) {
    e.preventDefault()
    run(async () => {
      await updateChain(editingId, { name: editName.trim(), applies_to_module: editModule })
      setEditingId(null)
    }, 'Approval chain updated.', 'Failed to update the chain.')
  }

  function handleDeleteChain(chain) {
    if (!confirm(`Delete the chain "${chain.name}" and all its steps?`)) return
    run(() => deleteChain(chain.id), 'Approval chain deleted.', 'Failed to delete the chain.')
  }

  function handleAddStep(chain) {
    const roleId = stepRole[chain.id]
    if (!roleId) {
      setError('Please choose a role for the new step.')
      return
    }
    run(async () => {
      await createStep({ approval_chain: chain.id, approver_role: roleId })
      setStepRole((prev) => ({ ...prev, [chain.id]: '' }))
    }, 'Step added.', 'Failed to add the step.')
  }

  function handleDeleteStep(step) {
    run(() => deleteStep(step.id), 'Step removed.', 'Failed to remove the step.')
  }

  function handleMove(chain, index, direction) {
    const ids = chain.steps.map((s) => s.id)
    const target = index + direction
    if (target < 0 || target >= ids.length) return
    ;[ids[index], ids[target]] = [ids[target], ids[index]]
    run(() => reorderChain(chain.id, ids), 'Step order updated.', 'Failed to change the order.')
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-[#14142B]">Approval Chains</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-6">
        Define who must approve a request, step by step. Each step is approved by anyone holding the chosen role.
      </p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}
      {message && <p className="text-sm text-[#16A34A] mb-4">{message}</p>}

      {canManage && (
        <form
          onSubmit={handleCreateChain}
          className="bg-white rounded-xl border border-[#EEEEF2] p-4 mb-6 flex flex-wrap gap-3 items-center"
        >
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Chain name (e.g. Leave Approval)"
            required
            className={`${inputClass} w-64`}
          />
          <select value={newModule} onChange={(e) => setNewModule(e.target.value)} className={inputClass}>
            {MODULES.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          <button
            type="submit"
            className="flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
          >
            <Plus size={16} /> New Chain
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : chains.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-14 flex flex-col items-center text-center">
          <GitBranch className="text-[#71717A]/40 mb-3" size={36} />
          <p className="text-sm text-[#71717A]">
            {canManage
              ? 'No approval chains yet. Create your first one above.'
              : 'No approval chains have been set up yet.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {chains.map((chain) => (
            <div key={chain.id} className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-4">
              {editingId === chain.id ? (
                <form onSubmit={handleSaveEdit} className="flex flex-wrap gap-2 items-center mb-3">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                    className={`${inputClass} w-64`}
                  />
                  <select value={editModule} onChange={(e) => setEditModule(e.target.value)} className={inputClass}>
                    {MODULES.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                  <button
                    type="submit"
                    className="bg-[#6C31D6] hover:bg-[#5A28B0] text-white rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="flex items-center gap-1 text-sm text-[#71717A] hover:text-[#14142B] px-2 py-2"
                  >
                    <X size={14} /> Cancel
                  </button>
                </form>
              ) : (
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-[#6C31D6]/10 text-[#6C31D6] flex items-center justify-center shrink-0">
                    <GitBranch size={16} />
                  </div>
                  <span className="text-sm font-semibold text-[#14142B]">{chain.name}</span>
                  <span className="text-xs bg-[#EDE9FE] text-[#6C31D6] rounded-full px-2.5 py-0.5">
                    {moduleLabel(chain.applies_to_module)}
                  </span>
                  {canManage && (
                    <div className="ml-auto flex items-center gap-1">
                      <button
                        onClick={() => startEdit(chain)}
                        title="Edit chain"
                        className="p-1.5 rounded-lg text-[#71717A] hover:bg-[#FAFAFA] hover:text-[#6C31D6] transition-colors"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        onClick={() => handleDeleteChain(chain)}
                        title="Delete chain"
                        className="p-1.5 rounded-lg text-[#71717A] hover:bg-[#FAFAFA] hover:text-[#DC2626] transition-colors"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  )}
                </div>
              )}

              {chain.steps.length === 0 ? (
                <p className="text-sm text-[#71717A] border border-dashed border-[#EEEEF2] rounded-lg px-3 py-4 text-center">
                  This chain has no steps yet.
                </p>
              ) : (
                <ol className="divide-y divide-[#EEEEF2] border border-[#EEEEF2] rounded-lg">
                  {chain.steps.map((step, index) => (
                    <li key={step.id} className="flex items-center gap-3 px-3 py-2 hover:bg-[#FAFAFA] transition-colors duration-150">
                      <span className="w-6 h-6 rounded-full bg-[#6C31D6]/10 text-[#6C31D6] text-xs font-semibold flex items-center justify-center">
                        {step.step_order}
                      </span>
                      <span className="text-sm text-[#14142B]">{step.approver_role_name}</span>
                      {canManage && (
                        <div className="ml-auto flex items-center gap-1">
                          <button
                            onClick={() => handleMove(chain, index, -1)}
                            disabled={index === 0}
                            title="Move up"
                            className="p-1.5 rounded-lg text-[#71717A] hover:bg-white hover:text-[#6C31D6] disabled:opacity-30 disabled:hover:text-[#71717A] transition-colors"
                          >
                            <ArrowUp size={14} />
                          </button>
                          <button
                            onClick={() => handleMove(chain, index, 1)}
                            disabled={index === chain.steps.length - 1}
                            title="Move down"
                            className="p-1.5 rounded-lg text-[#71717A] hover:bg-white hover:text-[#6C31D6] disabled:opacity-30 disabled:hover:text-[#71717A] transition-colors"
                          >
                            <ArrowDown size={14} />
                          </button>
                          <button
                            onClick={() => handleDeleteStep(step)}
                            title="Remove step"
                            className="p-1.5 rounded-lg text-[#71717A] hover:bg-white hover:text-[#DC2626] transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      )}
                    </li>
                  ))}
                </ol>
              )}

              {canManage && (
                <div className="flex gap-2 mt-3">
                  <select
                    value={stepRole[chain.id] || ''}
                    onChange={(e) => setStepRole((prev) => ({ ...prev, [chain.id]: e.target.value }))}
                    className={inputClass}
                  >
                    <option value="">Approver role...</option>
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleAddStep(chain)}
                    className="flex items-center gap-1.5 border border-[#6C31D6] text-[#6C31D6] hover:bg-[#EDE9FE] rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150"
                  >
                    <Plus size={14} /> Add Step
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ApprovalChainsPage
