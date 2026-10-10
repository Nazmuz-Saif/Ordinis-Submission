import { getActionsPage } from '../../services/adminService'
import { DataTable, Notice, PageHeader } from './shared'
import { formatDate } from './format'
import { usePagedList } from './usePagedList'

const LABELS = {
  suspend: 'Suspended company',
  activate: 'Activated company',
  resolve_ticket: 'Resolved ticket',
  reopen_ticket: 'Reopened ticket',
}

const columns = [
  { key: 'when', label: 'When', render: (a) => <span className="text-[#71717A] whitespace-nowrap">{formatDate(a.created_at)}</span> },
  { key: 'who', label: 'Who', render: (a) => <span className="whitespace-nowrap">{a.actor_email}</span> },
  { key: 'action', label: 'Action', render: (a) => LABELS[a.action] || a.action },
  { key: 'company', label: 'Company', render: (a) => <span className="font-medium whitespace-nowrap">{a.company_name}</span> },
  { key: 'note', label: 'Note', render: (a) => a.note || <span className="text-[#71717A]">-</span> },
]

function ActivityPage() {
  const list = usePagedList(getActionsPage)
  return (
    <div className="space-y-5">
      <PageHeader title="Activity" subtitle="What Platform Admins did: suspend, activate, tickets. This list cannot be edited." />
      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="activity-table" rowTestId="activity-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage} emptyTitle="No activity yet" emptyText="Suspensions and ticket changes appear here."
      />
    </div>
  )
}

export default ActivityPage
