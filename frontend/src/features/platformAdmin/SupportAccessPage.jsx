import { useEffect, useState } from 'react'
import { CheckCircle2, ShieldCheck, ShieldOff, XCircle } from 'lucide-react'
import {
  approveAccessRequest, denyAccessRequest, getAccessLogPage, getAccessRequestsPage, revokeAccessRequest,
} from '../../services/supportAccessService'
import { useAuth } from '../../store/AuthContext'
import StatusPill from '../../components/common/StatusPill'
import EmptyState from '../../components/common/EmptyState'
import Pagination from '../../components/common/Pagination'

const PERMISSION = 'approve_support_access'
const HOURS = [1, 2, 4, 8, 24, 48, 72]

const STATUS = {
  pending: { variant: 'warning', label: 'Pending' },
  approved: { variant: 'success', label: 'Active' },
  denied: { variant: 'failed', label: 'Denied' },
  revoked: { variant: 'neutral', label: 'Revoked' },
  expired: { variant: 'neutral', label: 'Expired' },
}

const formatDate = (value) => (value ? new Date(value).toLocaleString() : '')
const errorMessage = (err, fallback) => err.response?.data?.error?.message || fallback

const TABS = [
  { key: 'requests', label: 'Requests' },
  { key: 'log', label: 'Access log' },
]

function SupportAccessPage() {
  const { hasPermission } = useAuth()
  const allowed = hasPermission(PERMISSION)

  const [tab, setTab] = useState('requests')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null) // { items, count, pageSize, totalPages }
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [refresh, setRefresh] = useState(0)

  // dialog: { request, kind: 'approve' | 'deny' | 'revoke' } or null
  const [dialog, setDialog] = useState(null)
  const [hours, setHours] = useState(24)
  const [submitting, setSubmitting] = useState(false)
  const [dialogError, setDialogError] = useState('')

  useEffect(() => {
    if (!allowed) return
    let active = true
    const load = tab === 'requests' ? getAccessRequestsPage : getAccessLogPage
    load(page)
      .then((result) => {
        if (active) setData(result)
      })
      .catch((err) => {
        if (!active) return
        if (err.response?.status === 404 && page > 1) setPage(page - 1)
        else setError(errorMessage(err, 'Failed to load.'))
      })
    return () => {
      active = false
    }
  }, [allowed, tab, page, refresh])

  function switchTab(next) {
    setTab(next)
    setPage(1)
    setData(null)
    setError('')
  }

  function openDialog(request, kind) {
    setDialog({ request, kind })
    setHours(24)
    setDialogError('')
  }

  async function confirm() {
    const { request, kind } = dialog
    setSubmitting(true)
    setDialogError('')
    try {
      if (kind === 'approve') await approveAccessRequest(request.id, hours)
      else if (kind === 'deny') await denyAccessRequest(request.id)
      else await revokeAccessRequest(request.id)
      setMessage(
        kind === 'approve' ? `Access approved for ${hours} hour(s).`
          : kind === 'deny' ? 'Request denied.' : 'Access ended.',
      )
      setDialog(null)
      setRefresh((n) => n + 1)
    } catch (err) {
      setDialogError(errorMessage(err, 'Could not save your decision.'))
    } finally {
      setSubmitting(false)
    }
  }

  if (!allowed) {
    return (
      <EmptyState
        title="You do not have access to this page"
        description="Ask your company owner for the Approve Support Access permission."
      />
    )
  }

  const loading = !data && !error

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[#14142B]">Support access</h1>
        <p className="text-sm text-[#71717A] mt-1 max-w-2xl">
          Ordinis staff cannot see your company data unless you approve a request. Approved access is
          read-only, ends on time, and every use is written to the access log.
        </p>
      </div>

      {message && (
        <div role="status" data-testid="support-message" className="rounded-lg bg-[#16A34A]/10 text-[#15803D] px-4 py-3 text-sm">
          {message}
        </div>
      )}
      {error && (
        <div role="alert" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] px-4 py-3 text-sm">{error}</div>
      )}

      <div className="flex gap-1 border-b border-[#EEEEF2]">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            data-testid={`tab-${t.key}`}
            onClick={() => switchTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors duration-150 ${
              tab === t.key ? 'border-[#6C31D6] text-[#6C31D6]' : 'border-transparent text-[#71717A] hover:text-[#14142B]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div className="skeleton h-40 w-full rounded-xl" />}

      {data && tab === 'requests' && (
        data.items.length === 0 ? (
          <EmptyState title="No support requests" description="When Ordinis support asks for access, the request appears here." />
        ) : (
          <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm overflow-x-auto">
            <table data-testid="support-requests-table" className="w-full text-sm">
              <thead>
                <tr className="text-left text-[#71717A] border-b border-[#EEEEF2]">
                  <th className="px-4 py-3 font-medium">Requested by</th>
                  <th className="px-4 py-3 font-medium">Reason</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Requested</th>
                  <th className="px-4 py-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EEEEF2]">
                {data.items.map((r) => {
                  const s = STATUS[r.status] || STATUS.pending
                  return (
                    <tr key={r.id} data-testid="request-row" className="text-[#14142B]">
                      <td className="px-4 py-3 whitespace-nowrap">{r.requested_by_email}</td>
                      <td className="px-4 py-3 max-w-xs">{r.reason}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <StatusPill status={s.variant} label={s.label} />
                        {r.status === 'approved' && (
                          <p data-testid="request-expiry" className="text-xs text-[#71717A] mt-1">until {formatDate(r.expires_at)}</p>
                        )}
                        {r.decided_by_name && r.status !== 'pending' && (
                          <p className="text-xs text-[#71717A] mt-1">by {r.decided_by_name}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-[#71717A]">{formatDate(r.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          {r.status === 'pending' && (
                            <>
                              <button
                                type="button" data-testid="approve-btn" onClick={() => openDialog(r, 'approve')}
                                className="flex items-center gap-1.5 bg-[#16A34A] hover:bg-[#15803D] text-white rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150"
                              >
                                <CheckCircle2 size={15} /> Approve
                              </button>
                              <button
                                type="button" data-testid="deny-btn" onClick={() => openDialog(r, 'deny')}
                                className="flex items-center gap-1.5 border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150"
                              >
                                <XCircle size={15} /> Deny
                              </button>
                            </>
                          )}
                          {r.status === 'approved' && (
                            <button
                              type="button" data-testid="revoke-btn" onClick={() => openDialog(r, 'revoke')}
                              className="flex items-center gap-1.5 border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150"
                            >
                              <ShieldOff size={15} /> End access now
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )
      )}

      {data && tab === 'log' && (
        data.items.length === 0 ? (
          <EmptyState icon={ShieldCheck} title="No access yet" description="Nothing in your company has been read by Ordinis support." />
        ) : (
          <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm overflow-x-auto">
            <table data-testid="access-log-table" className="w-full text-sm">
              <thead>
                <tr className="text-left text-[#71717A] border-b border-[#EEEEF2]">
                  <th className="px-4 py-3 font-medium">When</th>
                  <th className="px-4 py-3 font-medium">Who</th>
                  <th className="px-4 py-3 font-medium">What was read</th>
                  <th className="px-4 py-3 font-medium">Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EEEEF2]">
                {data.items.map((e) => (
                  <tr key={e.id} data-testid="log-row" className="text-[#14142B]">
                    <td className="px-4 py-3 whitespace-nowrap text-[#71717A]">{formatDate(e.created_at)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">{e.actor_email}</td>
                    <td className="px-4 py-3">{e.detail}</td>
                    <td className="px-4 py-3 text-xs text-[#71717A] break-all">{e.method} {e.endpoint}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {data && (
        <Pagination page={page} totalPages={data.totalPages} count={data.count} pageSize={data.pageSize} onChange={setPage} />
      )}

      {dialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14142B]/40 p-4">
          <div role="dialog" className="bg-white rounded-xl shadow-xl w-full max-w-md p-5">
            <h2 className="text-lg font-semibold text-[#14142B]">
              {dialog.kind === 'approve' ? 'Approve support access' : dialog.kind === 'deny' ? 'Deny request' : 'End access now'}
            </h2>
            <p className="text-sm text-[#71717A] mt-1">
              {dialog.request.requested_by_email}: {dialog.request.reason}
            </p>

            {dialog.kind === 'approve' && (
              <label className="block mt-4 text-sm text-[#14142B]">
                Access lasts
                <select
                  data-testid="approve-hours" value={hours} onChange={(e) => setHours(Number(e.target.value))}
                  className="mt-1 w-full border border-[#EEEEF2] rounded-lg px-3 py-2 bg-white"
                >
                  {HOURS.map((h) => <option key={h} value={h}>{h} hour{h > 1 ? 's' : ''}</option>)}
                </select>
                <span className="block text-xs text-[#71717A] mt-1">Read-only. It ends by itself, and you can end it earlier.</span>
              </label>
            )}
            {dialog.kind === 'revoke' && (
              <p className="text-sm text-[#14142B] mt-4">Support will lose access immediately.</p>
            )}

            {dialogError && <p role="alert" className="text-sm text-[#DC2626] mt-3">{dialogError}</p>}

            <div className="flex justify-end gap-2 mt-5">
              <button type="button" onClick={() => setDialog(null)} className="px-4 py-2 text-sm rounded-lg border border-[#EEEEF2] text-[#14142B] hover:bg-[#FAFAFA]">
                Cancel
              </button>
              <button
                type="button" data-testid="confirm-btn" disabled={submitting} onClick={confirm}
                className={`px-4 py-2 text-sm rounded-lg text-white font-medium disabled:opacity-60 ${
                  dialog.kind === 'approve' ? 'bg-[#16A34A] hover:bg-[#15803D]' : 'bg-[#DC2626] hover:bg-[#B91C1C]'
                }`}
              >
                {dialog.kind === 'approve' ? 'Approve' : dialog.kind === 'deny' ? 'Deny' : 'End access'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SupportAccessPage
