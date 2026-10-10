import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCheck } from 'lucide-react'
import {
  announceInboxChange, getInboxPage, getInboxSummary, markAllNotificationsRead, markNotificationRead,
} from '../../services/notificationsService'
import EmptyState from '../../components/common/EmptyState'
import Pagination from '../../components/common/Pagination'
import InboxIcon from './InboxIcon'
import { KIND_LABEL } from './kinds'
import { timeAgo } from './timeAgo'

const SUMMARY = [
  { key: 'approvals', label: 'Approvals waiting' },
  { key: 'reviews', label: 'To review' },
  { key: 'tasks', label: 'My open tasks' },
  { key: 'unread', label: 'Unread notifications' },
]

function ActionInboxPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    let active = true
    Promise.all([getInboxPage(page), getInboxSummary()])
      .then(([list, counts]) => {
        if (!active) return
        if (list.items.length === 0 && page > 1) setPage(page - 1) // the last item of the last page is gone
        else {
          setData(list)
          setSummary(counts)
          setError('')
        }
      })
      .catch(() => {
        if (active) setError('Failed to load your inbox.')
      })
    return () => {
      active = false
    }
  }, [page, refresh])

  function changed() {
    setRefresh((n) => n + 1)
    announceInboxChange()
  }

  async function guarded(fn) {
    setError('')
    try {
      await fn()
      changed()
    } catch {
      setError('Could not update the notification.')
    }
  }

  async function open(item) {
    if (item.kind === 'notification') {
      try {
        await markNotificationRead(item.id)
        announceInboxChange()
      } catch {
        // opening the page matters more than the read mark
      }
    }
    if (item.link) navigate(item.link)
  }

  const loading = !data && !error

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-[#14142B]">Action Inbox</h1>
          <p className="text-sm text-[#71717A] mt-1">Everything that needs your attention, in one place.</p>
        </div>
        {summary?.unread > 0 && (
          <button
            type="button" data-testid="mark-all-read" onClick={() => guarded(markAllNotificationsRead)}
            className="flex items-center gap-1.5 border border-[#EEEEF2] bg-white hover:bg-[#FAFAFA] text-[#14142B] rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap"
          >
            <CheckCheck size={16} /> Mark all read
          </button>
        )}
      </div>

      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {SUMMARY.map((s) => (
            <div key={s.key} className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm px-4 py-3">
              <p className="text-xs text-[#71717A]">{s.label}</p>
              <p data-testid={`summary-${s.key}`} className="text-2xl font-bold text-[#14142B]">{summary[s.key]}</p>
            </div>
          ))}
        </div>
      )}

      {error && <div role="alert" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] px-4 py-3 text-sm">{error}</div>}
      {loading && <div className="skeleton h-48 w-full rounded-xl" />}

      {data && data.items.length === 0 && (
        <div data-testid="inbox-empty">
          <EmptyState title="You're all caught up" description="Nothing needs your attention right now." />
        </div>
      )}

      {data && data.items.length > 0 && (
        <ul data-testid="inbox-list" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm divide-y divide-[#EEEEF2]">
          {data.items.map((item) => (
            <li key={`${item.kind}-${item.id}`} data-testid="inbox-item" data-kind={item.kind}>
              <div className="flex items-center gap-3 px-4 py-3 hover:bg-[#FAFAFA] transition-colors duration-150">
                <button type="button" onClick={() => open(item)} className="flex flex-1 min-w-0 items-center gap-3 text-left">
                  <span className="shrink-0 h-9 w-9 rounded-lg bg-[#EDE9FE] text-[#6C31D6] flex items-center justify-center">
                    <InboxIcon kind={item.kind} />
                  </span>
                  <span className="min-w-0">
                    <span className="flex items-center gap-2">
                      <span data-testid="inbox-title" className="font-medium text-[#14142B] text-sm truncate">{item.title}</span>
                      <span className="shrink-0 rounded-full bg-[#EDE9FE] text-[#6C31D6] text-[11px] font-medium px-2 py-0.5">{KIND_LABEL[item.kind]}</span>
                      {item.overdue && <span data-testid="inbox-overdue" className="shrink-0 rounded-full bg-[#DC2626]/10 text-[#B91C1C] text-[11px] font-medium px-2 py-0.5">Overdue</span>}
                    </span>
                    <span className="block text-xs text-[#71717A] truncate">{item.subtitle}</span>
                  </span>
                </button>
                <span className="hidden sm:block shrink-0 text-xs text-[#71717A]">{timeAgo(item.created_at)}</span>
                {item.kind === 'notification' && (
                  <button
                    type="button" data-testid="mark-read-btn" onClick={() => guarded(() => markNotificationRead(item.id))}
                    className="shrink-0 text-xs font-medium text-[#6C31D6] border border-[#6C31D6] hover:bg-[#EDE9FE] rounded-lg px-2.5 py-1"
                  >
                    Mark read
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {data && <Pagination page={page} totalPages={data.totalPages} count={data.count} pageSize={data.pageSize} onChange={setPage} />}
    </div>
  )
}

export default ActionInboxPage
