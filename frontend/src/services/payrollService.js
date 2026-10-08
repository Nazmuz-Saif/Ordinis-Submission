import apiClient from './apiClient'
import { getAllPages } from './paging'

export async function getSalaryStructures() {
  return getAllPages('/payroll/salary-structures/')
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
