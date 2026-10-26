import { useState } from 'react'
import { ConfirmDialog } from './shared'

export const NOTE_MIN = 10

// A confirm dialog that will not go on without a written note (10 characters or more).
//   onConfirm(note)  returns a promise; a thrown server error is shown inside the dialog
//   children         the explanation above the text box
function NoteDialog({ title, confirmLabel, label, danger = false, maxLength = 255, onCancel, onConfirm, children, testId = 'company-note' }) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function confirm() {
    const trimmed = note.trim()
    if (trimmed.length < NOTE_MIN) {
      setError(trimmed ? `Write at least ${NOTE_MIN} characters (now ${trimmed.length}).` : `${label} is required: write at least ${NOTE_MIN} characters.`)
      return
    }
    setBusy(true)
    setError('')
    try {
      await onConfirm(trimmed)
    } catch (err) {
      setError(err.response?.data?.error?.message || 'This could not be saved. Try again.')
      setBusy(false)
    }
  }

  return (
    <ConfirmDialog title={title} confirmLabel={confirmLabel} danger={danger} busy={busy} error={error} onCancel={onCancel} onConfirm={confirm}>
      {children}
      <label htmlFor="note-dialog-text" className="block text-[#14142B] font-medium pt-1">{label}</label>
      <textarea
        id="note-dialog-text" data-testid={testId} rows={3} maxLength={maxLength} value={note} onChange={(e) => setNote(e.target.value)}
        className="w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm text-[#14142B] outline-none focus:border-[#6C31D6]"
      />
      <p className="text-xs text-[#71717A] text-right">{note.trim().length} / {maxLength}</p>
    </ConfirmDialog>
  )
}

export default NoteDialog
