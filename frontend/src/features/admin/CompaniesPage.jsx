import { useState } from 'react'
import { KeyRound, Power, PowerOff } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getCompaniesPage } from '../../services/adminService'
import StatusPill from '../../components/common/StatusPill'
import { DataTable, Notice, PageHeader } from './shared'
import CompanyStatusDialog from './CompanyStatusDialog'
import RequestAccessDialog from './RequestAccessDialog'
import { formatDate } from './format'
import { usePagedList } from './usePagedList'

function CompaniesPage() {
  const list = usePagedList(getCompaniesPage)
  const [dialog, setDialog] = useState(null) // { company, kind: 'suspend' | 'activate' | 'access' }
  const [message, setMessage] = useState('')

  function done(kind) {
    const { company } = dialog
    setMessage(kind === 'suspend' ? `${company.name} is suspended.` : `${company.name} is active again.`)
    setDialog(null)
    list.reload()
  }

  const columns = [
    { key: 'name', label: 'Company', render: (c) => (<><Link to={`/admin/companies/${c.id}`} data-testid="company-link" className="font-medium hover:text-[#6C31D6]">{c.name}</Link><p className="text-xs text-[#71717A]">{c.subdomain}</p></>) },
    { key: 'industry', label: 'Industry', render: (c) => c.industry || <span className="text-[#71717A]">-</span> },
    {
      key: 'status', label: 'Status',
      render: (c) => <StatusPill status={c.is_active ? 'success' : 'failed'} label={c.is_active ? 'Active' : 'Suspended'} />,
    },
    { key: 'tickets', label: 'Open tickets', render: (c) => c.open_tickets },
    { key: 'requests', label: 'Pending requests', render: (c) => c.pending_requests },
    { key: 'created', label: 'Joined', render: (c) => <span className="text-[#71717A] whitespace-nowrap">{formatDate(c.created_at)}</span> },
    {
      key: 'access', label: 'Access', align: 'right',
      render: (c) => (
        <button
          type="button" data-testid="request-access-btn" onClick={() => setDialog({ company: c, kind: 'access' })}
          className="inline-flex items-center gap-1.5 border border-[#EEEEF2] hover:border-[#A78BFA] rounded-lg px-3 py-1.5 text-sm font-medium text-[#14142B] whitespace-nowrap"
        >
          <KeyRound size={15} /> Request access
        </button>
      ),
    },
    {
      key: 'action', label: 'Action', align: 'right',
      render: (c) => c.is_active ? (
        <button
          type="button" data-testid="suspend-btn" onClick={() => setDialog({ company: c, kind: 'suspend' })}
          className="inline-flex items-center gap-1.5 border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1.5 text-sm font-medium"
        >
          <PowerOff size={15} /> Suspend
        </button>
      ) : (
        <button
          type="button" data-testid="activate-btn" onClick={() => setDialog({ company: c, kind: 'activate' })}
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
      {dialog && dialog.kind !== 'access' && <CompanyStatusDialog company={dialog.company} kind={dialog.kind} onCancel={() => setDialog(null)} onDone={done} />}
      {dialog?.kind === 'access' && (
        <RequestAccessDialog
          company={dialog.company} onCancel={() => setDialog(null)}
          onDone={() => { setMessage(`Access request sent to ${dialog.company.name}. It is Pending on the Access Requests page.`); setDialog(null); list.reload() }}
        />
      )}
    </div>
  )
}

export default CompaniesPage
