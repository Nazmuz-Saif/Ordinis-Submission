import { activateCompany, suspendCompany } from '../../services/adminService'
import NoteDialog from './NoteDialog'

// Suspend or activate one company. Both need a written note: it is saved in the action log.
//   kind      'suspend' | 'activate'
//   onDone    called after the server accepted the change
function CompanyStatusDialog({ company, kind, onCancel, onDone }) {
  const suspend = kind === 'suspend'

  async function confirm(note) {
    if (suspend) await suspendCompany(company.id, note)
    else await activateCompany(company.id, note)
    onDone(kind)
  }

  return (
    <NoteDialog
      title={suspend ? `Suspend ${company.name}?` : `Activate ${company.name}?`}
      confirmLabel={suspend ? 'Suspend company' : 'Activate company'}
      label={suspend ? 'Reason for the suspension' : 'Reason for activating'}
      danger={suspend} onCancel={onCancel} onConfirm={confirm}
    >
      {suspend ? (
        <>
          <p>Nobody in this company will be able to log in or use the app. Their data is kept.</p>
          <p>You can activate the company again at any time.</p>
        </>
      ) : (
        <p>Everyone in this company can log in and work again.</p>
      )}
    </NoteDialog>
  )
}

export default CompanyStatusDialog
