import { getAccessRequestsPage } from '../../services/adminService'
import StatusPill from '../../components/common/StatusPill'
import { DataTable, Notice, PageHeader } from './shared'
import { formatDate } from './format'
import { usePagedList } from './usePagedList'

const STATUS = {
  pending: { variant: 'warning', label: 'Pending' },
  approved: { variant: 'success', label: 'Active' },
  denied: { variant: 'failed', label: 'Denied' },
  revoked: { variant: 'neutral', label: 'Revoked' },
  expired: { variant: 'neutral', label: 'Expired' },
}

const columns = [
  { key: 'company', label: 'Company', render: (r) => <span className="font-medium whitespace-nowrap">{r.company_name}</span> },
  { key: 'by', label: 'Requested by', render: (r) => <span className="whitespace-nowrap">{r.requested_by_email}</span> },
  { key: 'reason', label: 'Reason', render: (r) => <span className="block max-w-xs">{r.reason}</span> },
  {
    key: 'status', label: 'Status',
    render: (r) => {
      const s = STATUS[r.status] || STATUS.pending
      return (
        <>
          <StatusPill status={s.variant} label={s.label} />
          {r.status === 'approved' && <p className="text-xs text-[#71717A] mt-1">until {formatDate(r.expires_at)}</p>}
        </>
      )
    },
  },
  { key: 'created', label: 'Requested', render: (r) => <span className="text-[#71717A] whitespace-nowrap">{formatDate(r.created_at)}</span> },
]

function AccessRequestsPage() {
  const list = usePagedList(getAccessRequestsPage)
  return (
    <div className="space-y-5">
      <PageHeader
        title="Access requests"
        subtitle="Break-Glass requests for company data. Only the company's CEO can approve one, and approved access ends by itself."
      />
      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="requests-table" rowTestId="request-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage} emptyTitle="No access requests" emptyText="Requests appear here when support asks a company for access."
      />
    </div>
  )
}

export default AccessRequestsPage
