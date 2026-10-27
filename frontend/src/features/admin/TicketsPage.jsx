import { useCallback, useState } from 'react'
import { getTicketsPage, reopenTicket, resolveTicket } from '../../services/adminService'
import StatusPill from '../../components/common/StatusPill'
import { DataTable, Notice, PageHeader } from './shared'
import { formatDate } from './format'
import { usePagedList } from './usePagedList'
import { personName } from '../../utils/people'
import NoteDialog from './NoteDialog'

const FILTERS = [
  { key: '', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'resolved', label: 'Resolved' },
]

function TicketsPage() {
  const [filter, setFilter] = useState('')
  const load = useCallback((page) => getTicketsPage(page, filter), [filter])
  const list = usePagedList(load, filter)
  const [error, setError] = useState('')
  const [resolving, setResolving] = useState(null)     // the ticket the resolution note is being written for

  async function reopen(ticket) {
    setError('')
    try {
      await reopenTicket(ticket.id)
      list.reload()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Could not update the ticket.')
    }
  }

  async function resolve(note) {
    await resolveTicket(resolving.id, note)
    setResolving(null)
    list.reload()
  }

  const columns = [
    { key: 'company', label: 'Company', render: (t) => <span className="font-medium whitespace-nowrap">{t.company_name}</span> },
    {
      key: 'subject', label: 'Ticket',
      render: (t) => (<><p className="font-medium">{t.subject}</p>{t.description && <p className="text-xs text-[#71717A] mt-0.5 max-w-md">{t.description}</p>}{t.resolution_note && <p data-testid="ticket-resolution" className="text-xs text-[#15803D] mt-1 max-w-md">Resolution: {t.resolution_note}</p>}</>),
    },
    { key: 'by', label: 'Raised by', render: (t) => <span className="whitespace-nowrap">{t.created_by_email ? personName(t.created_by_name, t.created_by_email) : '-'}</span> },
    {
      key: 'status', label: 'Status',
      render: (t) => <StatusPill status={t.status === 'open' ? 'warning' : 'success'} label={t.status === 'open' ? 'Open' : 'Resolved'} />,
    },
    { key: 'created', label: 'Raised', render: (t) => <span className="text-[#71717A] whitespace-nowrap">{formatDate(t.created_at)}</span> },
    {
      key: 'action', label: 'Action', align: 'right',
      render: (t) => t.status === 'open' ? (
        <button
          type="button" data-testid="resolve-btn" onClick={() => setResolving(t)}
          className="bg-[#16A34A] hover:bg-[#15803D] text-white rounded-lg px-3 py-1.5 text-sm font-medium"
        >
          Mark resolved
        </button>
      ) : (
        <button
          type="button" data-testid="reopen-btn" onClick={() => reopen(t)}
          className="border border-[#EEEEF2] text-[#14142B] hover:bg-[#FAFAFA] rounded-lg px-3 py-1.5 text-sm font-medium"
        >
          Reopen
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-5">
      <PageHeader title="Support tickets" subtitle="Problems reported by companies." />
      <div className="flex gap-1 border-b border-[#EEEEF2]">
        {FILTERS.map((f) => (
          <button
            key={f.key || 'all'} type="button" data-testid={`filter-${f.key || 'all'}`} onClick={() => setFilter(f.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-150 ${
              filter === f.key ? 'border-[#6C31D6] text-[#6C31D6]' : 'border-transparent text-[#71717A] hover:text-[#14142B]'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
      {(error || list.error) && <Notice>{error || list.error}</Notice>}
      <DataTable
        testId="tickets-table" rowTestId="ticket-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage} emptyTitle="No tickets" emptyText="Nothing to show for this filter."
      />
      {resolving && (
        <NoteDialog
          title="Mark this ticket resolved?" confirmLabel="Mark resolved" label="Resolution note" maxLength={500} testId="resolution-note"
          onCancel={() => setResolving(null)} onConfirm={resolve}
        >
          <p>{resolving.company_name}: {resolving.subject}</p>
          <p>The person who raised it can read this note. Say what was done.</p>
        </NoteDialog>
      )}
    </div>
  )
}

export default TicketsPage
