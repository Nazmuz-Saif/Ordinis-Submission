import { useState } from 'react'
import { activateCompany, suspendCompany } from '../../services/adminService'
import { ConfirmDialog } from './shared'

// Suspend or activate one company, with a note for the action log. A suspension needs a reason; an activation may skip it.
//   kind      'suspend' | 'activate'
//   onDone    called after the server accepted the change
function CompanyStatusDialog({ company, kind, onCancel, onDone }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const suspend = kind === 'suspend'

  async function confirm() {
    if (suspend && !note.trim()) {
      setError('Write a short reason for the suspension.')
      return
    }
    setBusy(true)
    setError('')
    try {
      if (suspend) await suspendCompany(company.id, note.trim())
      else await activateCompany(company.id, note.trim())
      onDone(kind)
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Could not change the company.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog
      title={suspend ? `Suspend ${company.name}?` : `Activate ${company.name}?`}
      confirmLabel={suspend ? 'Suspend company' : 'Activate company'}
      danger={suspend} busy={busy} error={error} onCancel={onCancel} onConfirm={confirm}
    >
      {suspend ? (
        <>
          <p>Nobody in this company will be able to log in or use the app. Their data is kept.</p>
          <p>You can activate the company again at any time.</p>
        </>
      ) : (
        <p>Everyone in this company can log in and work again.</p>
      )}
      <label htmlFor="company-note" className="block text-[#14142B] font-medium pt-1">{suspend ? 'Reason' : 'Note (optional)'}</label>
      <textarea
        id="company-note" data-testid="company-note" rows={3} maxLength={255} value={note} onChange={(e) => setNote(e.target.value)}
        className="w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm text-[#14142B] outline-none focus:border-[#6C31D6]"
      />
    </ConfirmDialog>
  )
}

export default CompanyStatusDialog
