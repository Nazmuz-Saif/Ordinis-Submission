import apiClient from './apiClient'
import { getPage } from './paging'

const BASE = '/notifications'

// Everything that needs MY attention: approvals waiting, tasks to do or review, unread notifications.
export const getInboxPage = (page = 1) => getPage(`${BASE}/inbox/`, { page })

export async function getInboxSummary() {
  const res = await apiClient.get(`${BASE}/inbox/summary/`)
  return res.data // { total, approvals, tasks, reviews, unread }
}

export async function markNotificationRead(id) {
  const res = await apiClient.post(`${BASE}/${id}/read/`)
  return res.data
}

export async function markAllNotificationsRead() {
  const res = await apiClient.post(`${BASE}/read-all/`)
  return res.data
}

// The bell and the inbox page are separate components. After a change, the page calls this and the bell refreshes.
export const INBOX_CHANGED = 'ordinis:inbox-changed'
export const announceInboxChange = () => window.dispatchEvent(new Event(INBOX_CHANGED))
