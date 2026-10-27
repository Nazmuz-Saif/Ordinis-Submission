import { useState } from 'react'
import { createAccessRequest } from '../../services/adminService'
import { ConfirmDialog } from './shared'

// Ask one company's CEO for time-limited, read-only access (Break-Glass). The request starts as Pending.
//   onDone  called after the server created the request
function RequestAccessDialog({ company, onCancel, onDone }) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function send() {
    if (!reason.trim()) {
      setError('Give a reason for the access request.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await createAccessRequest(company.id, reason.trim())
      onDone()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Could not send the request.')
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog title={`Request access to ${company.name}?`} confirmLabel="Send request" busy={busy} error={error} onCancel={onCancel} onConfirm={send}>
      <p>The company's CEO decides. If approved, you can read a short list of its records for a limited time and every read is logged.</p>
      <label htmlFor="access-reason" className="block text-[#14142B] font-medium pt-1">Reason</label>
      <textarea
        id="access-reason" data-testid="access-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
        className="w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm text-[#14142B] outline-none focus:border-[#6C31D6]"
      />
    </ConfirmDialog>
  )
}

export default RequestAccessDialog
