import apiClient from './apiClient'
import { getPage } from './paging'

const BASE = '/platform-admin/company/tickets'

// The signed-in person's own support tickets, newest first (a CEO also sees the company's).
export const getMyTicketsPage = (page = 1) => getPage(`${BASE}/`, { page, pageSize: 10 })

export async function createTicket(subject, description) {
  const res = await apiClient.post(`${BASE}/`, { subject, description })
  return res.data
}
