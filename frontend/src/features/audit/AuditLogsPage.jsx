import { useCallback, useEffect, useState } from 'react'
import { Download, ScrollText } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { downloadAuditExport, getAuditLogsPage, getAuditModules } from '../../services/auditLogService'
import EmptyState from '../../components/common/EmptyState'
import StatusPill from '../../components/common/StatusPill'
import { DataTable, Notice, PageHeader } from '../admin/shared'
import { usePagedList } from '../admin/usePagedList'
import { actionText, formatWhen, moduleLabel } from './auditFormat'
import { personName } from '../../utils/people'

const field = 'border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm bg-white outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15'
const ACTIONS = [['create', 'Created'], ['update', 'Updated'], ['delete', 'Deleted'], ['read', 'Break-Glass read'], ['export', 'Exported'], ['denied', 'Refused']]
const STATUSES = [['success', 'Success'], ['warning', 'Warning'], ['failed', 'Failed']]

function AuditLogsPage() {
  const { hasPermission } = useAuth()
  const allowed = hasPermission('view_audit_log')

  const [filters, setFilters] = useState({ module: '', action: '', status: '', q: '', date_from: '', date_to: '' })
  const filterKey = JSON.stringify(filters)
  const load = useCallback((page) => getAuditLogsPage(page, filters), [filters])
  const list = usePagedList(load, filterKey)
  const [modules, setModules] = useState([])
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')

  useEffect(() => {
    if (!allowed) return
    getAuditModules().then(setModules).catch(() => setModules([]))
  }, [allowed])

  const set = (name) => (e) => setFilters((f) => ({ ...f, [name]: e.target.value }))
  const anyFilter = Object.values(filters).some(Boolean)

  async function exportCsv() {
    setExporting(true)
    setExportError('')
    try {
      await downloadAuditExport(filters)
    } catch {
      setExportError('Could not export the audit log.')
    } finally {
      setExporting(false)
    }
  }

  if (!allowed) {
    return <EmptyState icon={ScrollText} title="You do not have access to this page" description="Reading the audit log needs the View Audit Log permission." />
  }

  const columns = [
    { key: 'user', label: 'User', render: (r) => <span data-testid="audit-user" className="font-medium">{r.actor_email ? personName(r.actor_name, r.actor_email) : 'Unknown'}</span> },
    {
      key: 'action', label: 'Action',
      render: (r) => (
        <>
          <p data-testid="audit-action">{actionText(r)}</p>
          {r.action !== 'denied' && r.action !== 'read' && r.object_repr && <p className="text-xs text-[#71717A]">{r.object_repr}</p>}
          {r.changed_fields?.length > 0 && <p className="text-xs text-[#71717A]">Changed: {r.changed_fields.join(', ')}</p>}
          {r.action === 'denied' && <p className="text-xs text-[#71717A]">{r.object_repr}</p>}
        </>
      ),
    },
    {
      key: 'module', label: 'Module',
      render: (r) => <span data-testid="audit-module" className="inline-block rounded-full bg-[#EDE9FE] text-[#6C31D6] px-2.5 py-0.5 text-xs font-medium capitalize">{moduleLabel(r.module)}</span>,
    },
    { key: 'when', label: 'Date & Time', render: (r) => <span className="whitespace-nowrap">{formatWhen(r.created_at)}</span> },
    { key: 'status', label: 'Status', render: (r) => <StatusPill status={r.status} /> },
  ]

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <PageHeader title="Audit Logs" subtitle="All system activity, tamper-proof. Rows are only added by the system: nobody can edit or delete them." />
        <button
          type="button" data-testid="audit-export" onClick={exportCsv} disabled={exporting}
          className="flex items-center gap-2 border border-[#EEEEF2] bg-white hover:bg-[#FAFAFA] rounded-lg px-4 py-2 text-sm font-medium text-[#14142B] disabled:opacity-60 transition-colors duration-150 shrink-0"
        >
          <Download size={16} /> {exporting ? 'Exporting...' : 'Export'}
        </button>
      </div>

      {exportError && <Notice testId="audit-export-error">{exportError}</Notice>}

      <div data-testid="audit-filters" className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-[#14142B]">
          Module
          <select data-testid="audit-filter-module" value={filters.module} onChange={set('module')} className={field + ' block mt-1'}>
            <option value="">All Modules</option>
            {modules.map((m) => <option key={m} value={m}>{moduleLabel(m)}</option>)}
          </select>
        </label>
        <label className="text-sm text-[#14142B]">
          Action
          <select data-testid="audit-filter-action" value={filters.action} onChange={set('action')} className={field + ' block mt-1'}>
            <option value="">All actions</option>
            {ACTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="text-sm text-[#14142B]">
          Status
          <select data-testid="audit-filter-status" value={filters.status} onChange={set('status')} className={field + ' block mt-1'}>
            <option value="">All statuses</option>
            {STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="text-sm text-[#14142B]">
          From
          <input data-testid="audit-filter-from" type="date" value={filters.date_from} onChange={set('date_from')} className={field + ' block mt-1'} />
        </label>
        <label className="text-sm text-[#14142B]">
          To
          <input data-testid="audit-filter-to" type="date" value={filters.date_to} onChange={set('date_to')} className={field + ' block mt-1'} />
        </label>
        <label className="text-sm text-[#14142B]">
          Search
          <input data-testid="audit-filter-q" placeholder="User or record" value={filters.q} onChange={set('q')} className={field + ' block mt-1 w-52'} />
        </label>
        {anyFilter && (
          <button type="button" data-testid="audit-clear" onClick={() => setFilters({ module: '', action: '', status: '', q: '', date_from: '', date_to: '' })} className="text-sm text-[#6C31D6] hover:underline pb-2">
            Clear filters
          </button>
        )}
      </div>

      {list.error && <Notice>{list.error}</Notice>}
      <DataTable
        testId="audit-table" rowTestId="audit-row" columns={columns} rows={list.data?.items ?? []}
        list={list} page={list.page} onPage={list.setPage}
        emptyTitle={anyFilter ? 'No matching activity' : 'No activity yet'} emptyText={anyFilter ? 'Try other filters.' : 'Actions in this company appear here.'}
      />
    </div>
  )
}

export default AuditLogsPage
