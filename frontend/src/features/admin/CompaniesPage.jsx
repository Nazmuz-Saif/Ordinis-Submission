import { useState } from 'react'
import { Power, PowerOff } from 'lucide-react'
import { activateCompany, getCompaniesPage, suspendCompany } from '../../services/adminService'
import StatusPill from '../../components/common/StatusPill'
import { ConfirmDialog, DataTable, Notice, PageHeader } from './shared'
import { formatDate } from './format'
import { usePagedList } from './usePagedList'

function CompaniesPage() {
  const list = usePagedList(getCompaniesPage)
  const [dialog, setDialog] = useState(null) // { company, kind: 'suspend' | 'activate' }
  const [busy, setBusy] = useState(false)
  const [dialogError, setDialogError] = useState('')
  const [message, setMessage] = useState('')

  async function confirm() {
    const { company, kind } = dialog
    setBusy(true)
    setDialogError('')
    try {
      if (kind === 'suspend') await suspendCompany(company.id)
      else await activateCompany(company.id)
      setMessage(kind === 'suspend' ? `${company.name} is suspended.` : `${company.name} is active again.`)
      setDialog(null)
      list.reload()
    } catch (err) {
      setDialogError(err.response?.data?.error?.message || 'Could not change the company.')
    } finally {
      setBusy(false)
    }
  }

  const columns = [
    { key: 'name', label: 'Company', render: (c) => (<><p className="font-medium">{c.name}</p><p className="text-xs text-[#71717A]">{c.subdomain}</p></>) },
    { key: 'industry', label: 'Industry', render: (c) => c.industry || <span className="text-[#71717A]">-</span> },
    {
      key: 'status', label: 'Status',
      render: (c) => <StatusPill status={c.is_active ? 'success' : 'failed'} label={c.is_active ? 'Active' : 'Suspended'} />,
    },
    { key: 'tickets', label: 'Open tickets', render: (c) => c.open_tickets },
    { key: 'requests', label: 'Pending requests', render: (c) => c.pending_requests },
    { key: 'created', label: 'Joined', render: (c) => <span className="text-[#71717A] whitespace-nowrap">{formatDate(c.created_at)}</span> },
    {
      key: 'action', label: 'Action', align: 'right',
      render: (c) => c.is_active ? (
        <button
          type="button" data-testid="suspend-btn" onClick={() => { setDialog({ company: c, kind: 'suspend' }); setDialogError('') }}
          className="inline-flex items-center gap-1.5 border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1.5 text-sm font-medium"
        >
          <PowerOff size={15} /> Suspend
        </button>
      ) : (
        <button
          type="button" data-testid="activate-btn" onClick={() => { setDialog({ company: c, kind: 'activate' }); setDialogError('') }}
          className="inline-flex items-center gap-1.5 bg-[#16A34A] hover:bg-[#15803D] text-white rounded-lg px-3 py-1.5 text-sm font-medium"
        >
          <Power size={15} /> Activate
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-5">
      <PageHeader title="Companies" subtitle="Every company on Ordinis. You see who they are, never their employees, tasks or salaries." />
      {message && <Notice kind="success" testId="admin-message">{message}</Notice>}
      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="companies-table" rowTestId="company-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage} emptyTitle="No companies yet" emptyText="Companies appear here when they register."
      />
      {dialog && (
        <ConfirmDialog
          title={dialog.kind === 'suspend' ? `Suspend ${dialog.company.name}?` : `Activate ${dialog.company.name}?`}
          confirmLabel={dialog.kind === 'suspend' ? 'Suspend company' : 'Activate company'}
          danger={dialog.kind === 'suspend'} busy={busy} error={dialogError}
          onCancel={() => setDialog(null)} onConfirm={confirm}
        >
          {dialog.kind === 'suspend' ? (
            <>
              <p>Nobody in this company will be able to log in or use the app. Their data is kept.</p>
              <p>You can activate the company again at any time.</p>
            </>
          ) : (
            <p>Everyone in this company can log in and work again.</p>
          )}
        </ConfirmDialog>
      )}
    </div>
  )
}

export default CompaniesPage
