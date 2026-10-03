import { useEffect, useState } from 'react'
import { CheckCircle2, ClipboardCheck, XCircle } from 'lucide-react'
import { getInstances, approveInstance, rejectInstance } from '../../services/approvalsService'

const STATUS_STYLE = {
  pending: 'bg-[#F59E0B]/10 text-[#B45309]',
  approved: 'bg-[#16A34A]/10 text-[#15803D]',
  rejected: 'bg-[#DC2626]/10 text-[#B91C1C]',
}

const TABS = [
  { key: 'pending', label: 'Awaiting my action' },
  { key: 'all', label: 'All requests' },
]

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

function formatDate(value) {
  return new Date(value).toLocaleString()
}

function PendingApprovalsPage() {
  const [tab, setTab] = useState('pending')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  // dialog state: { instance, decision } or null
  const [dialog, setDialog] = useState(null)
  const [comment, setComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [dialogError, setDialogError] = useState('')

  async function load(activeTab) {
    try {
      setItems(await getInstances(activeTab === 'pending'))
    } catch (err) {
      setError(errorMessage(err, 'Failed to load requests.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    getInstances(true)
      .then((data) => {
        if (active) setItems(data)
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, 'Failed to load requests.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  function switchTab(next) {
    setTab(next)
    setError('')
    setMessage('')
    setLoading(true)
    load(next)
  }

  function openDialog(instance, decision) {
    setDialog({ instance, decision })
    setComment('')
    setDialogError('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const { instance, decision } = dialog
    if (decision === 'reject' && !comment.trim()) {
      setDialogError('A comment is required when rejecting.')
      return
    }
    setSubmitting(true)
    setDialogError('')
    try {
      if (decision === 'approve') await approveInstance(instance.id, comment.trim())
      else await rejectInstance(instance.id, comment.trim())
      setDialog(null)
      setMessage(decision === 'approve' ? 'Request approved.' : 'Request rejected.')
      await load(tab)
    } catch (err) {
      setDialogError(errorMessage(err, 'The action failed.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-[#14142B]">Approvals</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-5">
        Requests that need your decision, and the history of requests you are part of.
      </p>

      <div className="flex gap-1 mb-5 border-b border-[#EEEEF2]">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => switchTab(t.key)}
            className={`px-4 py-2 text-sm font-medium -mb-px border-b-2 transition-colors duration-150 ${
              tab === t.key
                ? 'border-[#6C31D6] text-[#6C31D6]'
                : 'border-transparent text-[#71717A] hover:text-[#14142B]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}
      {message && <p className="text-sm text-[#16A34A] mb-4">{message}</p>}

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-[#EEEEF2] py-14 flex flex-col items-center text-center">
          <ClipboardCheck className="text-[#71717A]/40 mb-3" size={36} />
          <p className="text-sm text-[#71717A]">
            {tab === 'pending' ? 'Nothing is waiting for your decision.' : 'No requests yet.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <div key={item.id} className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-sm font-semibold text-[#14142B]">{item.chain_name}</span>
                <span className={`text-xs rounded-full px-2.5 py-0.5 capitalize ${STATUS_STYLE[item.status]}`}>
                  {item.status}
                </span>
                {item.status === 'pending' && (
                  <span className="text-xs text-[#71717A]">
                    Step {item.current_step} of {item.total_steps} · waiting for {item.current_step_role_name}
                  </span>
                )}
                {item.can_act && (
                  <div className="ml-auto flex gap-2">
                    <button
                      onClick={() => openDialog(item, 'approve')}
                      className="flex items-center gap-1.5 bg-[#16A34A] hover:bg-[#15803D] text-white rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150"
                    >
                      <CheckCircle2 size={15} /> Approve
                    </button>
                    <button
                      onClick={() => openDialog(item, 'reject')}
                      className="flex items-center gap-1.5 border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150"
                    >
                      <XCircle size={15} /> Reject
                    </button>
                  </div>
                )}
              </div>

              <p className="text-sm text-[#14142B] mt-2">{item.target_repr}</p>
              <p className="text-xs text-[#71717A] mt-0.5">
                Requested by {item.requested_by_email} · {formatDate(item.created_at)}
              </p>

              {item.actions.length > 0 && (
                <ul className="mt-3 space-y-1.5 border-t border-[#EEEEF2] pt-3">
                  {item.actions.map((a) => (
                    <li key={a.id} className="text-xs text-[#71717A]">
                      <span className={a.decision === 'approved' ? 'text-[#15803D]' : 'text-[#B91C1C]'}>
                        Step {a.step_order} {a.decision}
                      </span>{' '}
                      by {a.actor_email} · {formatDate(a.created_at)}
                      {a.comment && <span className="block text-[#14142B] mt-0.5">“{a.comment}”</span>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {dialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14142B]/40 p-4">
          <form
            onSubmit={handleSubmit}
            className="bg-white rounded-xl shadow-xl w-full max-w-md p-5"
          >
            <h2 className="text-lg font-semibold text-[#14142B]">
              {dialog.decision === 'approve' ? 'Approve request' : 'Reject request'}
            </h2>
            <p className="text-sm text-[#71717A] mt-1">
              {dialog.instance.chain_name} · {dialog.instance.target_repr}
            </p>
            <label className="block text-sm font-medium text-[#14142B] mt-4 mb-1">
              Comment {dialog.decision === 'approve' ? '(optional)' : '(required)'}
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition"
            />
            {dialogError && <p className="text-sm text-[#DC2626] mt-2">{dialogError}</p>}
            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => setDialog(null)}
                className="px-4 py-2 text-sm text-[#71717A] hover:text-[#14142B]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className={`px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-60 transition-colors duration-150 ${
                  dialog.decision === 'approve'
                    ? 'bg-[#16A34A] hover:bg-[#15803D]'
                    : 'bg-[#DC2626] hover:bg-[#B91C1C]'
                }`}
              >
                {dialog.decision === 'approve' ? 'Approve' : 'Reject'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

export default PendingApprovalsPage
