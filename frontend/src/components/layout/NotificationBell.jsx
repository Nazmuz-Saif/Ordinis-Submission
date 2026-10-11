import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell } from 'lucide-react'
import {
  INBOX_CHANGED, announceInboxChange, getInboxPage, getInboxSummary, markNotificationRead,
} from '../../services/notificationsService'
import useClickOutside from '../../hooks/useClickOutside'
import EmptyState from '../common/EmptyState'
import InboxIcon from '../../features/inbox/InboxIcon'
import { timeAgo } from '../../features/inbox/timeAgo'

const REFRESH_MS = 60000
const PREVIEW = 5

// The bell: a badge with how many things need me, and a short preview of the Action Inbox.
function NotificationBell() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [total, setTotal] = useState(0)
  const [items, setItems] = useState(null)
  const ref = useRef(null)
  const close = useCallback(() => setOpen(false), [])
  useClickOutside(ref, close, open)

  // the badge: now, every minute, and whenever the inbox page changes something
  useEffect(() => {
    let active = true
    const load = () => {
      getInboxSummary()
        .then((s) => { if (active) setTotal(s.total) })
        .catch(() => {}) // a failed refresh keeps the last number
    }
    load()
    const timer = setInterval(load, REFRESH_MS)
    window.addEventListener(INBOX_CHANGED, load)
    return () => {
      active = false
      clearInterval(timer)
      window.removeEventListener(INBOX_CHANGED, load)
    }
  }, [])

  // the preview, loaded each time the dropdown opens
  useEffect(() => {
    if (!open) return undefined
    let active = true
    getInboxPage(1)
      .then((page) => { if (active) setItems(page.items.slice(0, PREVIEW)) })
      .catch(() => { if (active) setItems([]) })
    return () => {
      active = false
    }
  }, [open])

  async function openItem(item) {
    setOpen(false)
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

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => { setItems(null); setOpen((v) => !v) }}
        aria-label="Notifications" aria-expanded={open} data-testid="notification-bell"
        className="relative p-2 rounded-lg text-[#14142B] hover:bg-white transition-colors duration-150"
      >
        <Bell size={19} />
        {total > 0 && (
          <span data-testid="notification-badge" className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-[#6C31D6] text-white text-[10px] font-semibold flex items-center justify-center">
            {total > 99 ? '99+' : total}
          </span>
        )}
      </button>
      {open && (
        <div data-testid="notification-dropdown" className="absolute right-0 mt-2 w-80 bg-white rounded-xl border border-[#EEEEF2] shadow-lg p-3">
          <div className="flex items-center justify-between px-1 pb-2">
            <p className="text-sm font-semibold text-[#14142B]">Action Inbox</p>
            {total > 0 && <span className="rounded-full bg-[#EDE9FE] text-[#6C31D6] text-xs font-semibold px-2 py-0.5">{total} new</span>}
          </div>
          {items === null && <div className="skeleton h-16 w-full rounded-lg" />}
          {items && items.length === 0 && <EmptyState title="You're all caught up" description="Nothing needs your attention." />}
          {items && items.length > 0 && (
            <ul>
              {items.map((item) => (
                <li key={`${item.kind}-${item.id}`}>
                  <button
                    type="button" data-testid="bell-item" onClick={() => openItem(item)}
                    className="w-full flex items-start gap-2.5 text-left px-2 py-2 rounded-lg hover:bg-[#FAFAFA]"
                  >
                    <span className="mt-0.5 text-[#6C31D6]"><InboxIcon kind={item.kind} size={16} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-[#14142B] truncate">{item.title}</span>
                      <span className="block text-xs text-[#71717A] truncate">{item.subtitle}</span>
                    </span>
                    <span className="text-[11px] text-[#71717A] whitespace-nowrap">{timeAgo(item.created_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button
            type="button" data-testid="bell-open-inbox" onClick={() => { setOpen(false); navigate('/inbox') }}
            className="mt-2 w-full text-center text-sm font-medium text-[#6C31D6] hover:bg-[#EDE9FE] rounded-lg py-2"
          >
            Open Action Inbox
          </button>
        </div>
      )}
    </div>
  )
}

export default NotificationBell
