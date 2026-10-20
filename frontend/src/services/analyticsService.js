import apiClient from './apiClient'

// Analytics is read-only: the page only ever reads the numbers of the user's own company.
export async function getOverview() {
  const res = await apiClient.get('/analytics/overview/')
  return res.data.data
}
