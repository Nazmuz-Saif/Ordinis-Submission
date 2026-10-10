import apiClient from './apiClient'

// Only the sections the user's Permissions allow come back (me, team, people, finance).
export async function getDashboardSummary() {
  const res = await apiClient.get('/dashboard/summary/')
  return res.data
}
