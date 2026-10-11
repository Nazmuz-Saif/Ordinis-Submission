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

// ---- Payslips (ST-127) ----
// filters: { mine: true } = only my own (finance sees the whole company otherwise), { month: '2026-10' }
export async function getPayslipsPage(page = 1, filters = {}) {
  const params = {}
  if (filters.mine) params.mine = 'true'
  if (filters.month) params.month = filters.month
  const res = await apiClient.get('/payroll/payslips/', { params: { ...params, page, page_size: 20 } })
  const body = res.data
  const items = body.data
  return { items, count: body.pagination.count, page, pageSize: 20, totalPages: Math.max(1, Math.ceil(body.pagination.count / 20)) }
}

export async function getPayslip(id) {
  const res = await apiClient.get(`/payroll/payslips/${id}/`)
  return res.data
}

// payload: { employee, month: 'YYYY-MM', deductions?, deduction_note? }. Amounts come from the Salary Structure.
export async function generatePayslip(payload) {
  const res = await apiClient.post('/payroll/payslips/', payload)
  return res.data
}

export async function voidPayslip(id) {
  await apiClient.delete(`/payroll/payslips/${id}/`)
}
