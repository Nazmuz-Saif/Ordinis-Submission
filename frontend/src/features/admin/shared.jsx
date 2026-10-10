import EmptyState from '../../components/common/EmptyState'
import Pagination from '../../components/common/Pagination'

export function PageHeader({ title, subtitle }) {
  return (
    <div>
      <h1 className="text-xl font-bold text-[#14142B]">{title}</h1>
      {subtitle && <p className="text-sm text-[#71717A] mt-1 max-w-2xl">{subtitle}</p>}
    </div>
  )
}

export function Notice({ kind = 'error', children, testId }) {
  const tone = kind === 'error' ? 'bg-[#DC2626]/10 text-[#B91C1C]' : 'bg-[#16A34A]/10 text-[#15803D]'
  return (
    <div role={kind === 'error' ? 'alert' : 'status'} data-testid={testId} className={`rounded-lg px-4 py-3 text-sm ${tone}`}>
      {children}
    </div>
  )
}

// columns: [{ key, label, align?, render(row) }]
export function DataTable({ testId, rowTestId, columns, rows, list, page, onPage, emptyTitle, emptyText }) {
  if (list.loading) return <div className="skeleton h-40 w-full rounded-xl" />
  if (!list.data) return null
  return (
    <>
      {rows.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyText} />
      ) : (
        <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm overflow-x-auto">
          <table data-testid={testId} className="w-full text-sm">
            <thead>
              <tr className="text-left text-[#71717A] border-b border-[#EEEEF2]">
                {columns.map((c) => (
                  <th key={c.key} className={`px-4 py-3 font-medium ${c.align === 'right' ? 'text-right' : ''}`}>{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEEEF2]">
              {rows.map((row) => (
                <tr key={row.id} data-testid={rowTestId} className="text-[#14142B]">
                  {columns.map((c) => (
                    <td key={c.key} className={`px-4 py-3 ${c.align === 'right' ? 'text-right' : ''}`}>{c.render(row)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Pagination page={page} totalPages={list.data.totalPages} count={list.data.count} pageSize={list.data.pageSize} onChange={onPage} />
    </>
  )
}

export function ConfirmDialog({ title, children, confirmLabel, danger, busy, error, onCancel, onConfirm }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14142B]/40 p-4">
      <div role="dialog" className="bg-white rounded-xl shadow-xl w-full max-w-md p-5">
        <h2 className="text-lg font-semibold text-[#14142B]">{title}</h2>
        <div className="text-sm text-[#71717A] mt-2 space-y-2">{children}</div>
        {error && <p role="alert" className="text-sm text-[#DC2626] mt-3">{error}</p>}
        <div className="flex justify-end gap-2 mt-5">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-sm rounded-lg border border-[#EEEEF2] text-[#14142B] hover:bg-[#FAFAFA]">
            Cancel
          </button>
          <button
            type="button" data-testid="confirm-btn" disabled={busy} onClick={onConfirm}
            className={`px-4 py-2 text-sm rounded-lg text-white font-medium disabled:opacity-60 ${
              danger ? 'bg-[#DC2626] hover:bg-[#B91C1C]' : 'bg-[#6C31D6] hover:bg-[#5B27B8]'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
