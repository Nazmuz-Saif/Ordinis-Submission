import apiClient from './apiClient'

export async function getSalaryStructures() {
  const res = await apiClient.get('/payroll/salary-structures/')
  return res.data
}

export async function createSalaryStructure(payload) {
  const res = await apiClient.post('/payroll/salary-structures/', payload)
  return res.data
}

export async function updateSalaryStructure(id, payload) {
  const res = await apiClient.patch(`/payroll/salary-structures/${id}/`, payload)
  return res.data
}

export async function deleteSalaryStructure(id) {
  const res = await apiClient.delete(`/payroll/salary-structures/${id}/`)
  return res.data
}