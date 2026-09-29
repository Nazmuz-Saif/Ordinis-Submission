import apiClient from './apiClient'

export async function getDepartments() {
  const res = await apiClient.get('/organization/departments/')
  return res.data
}

export async function createDepartment(name) {
  const res = await apiClient.post('/organization/departments/', { name })
  return res.data
}

export async function getDesignations() {
  const res = await apiClient.get('/organization/designations/')
  return res.data
}

export async function createDesignation(title) {
  const res = await apiClient.post('/organization/designations/', { title })
  return res.data
}

export async function getEmployees() {
  const res = await apiClient.get('/organization/employees/')
  return res.data
}

export async function createEmployee(payload) {
  const res = await apiClient.post('/organization/employees/', payload)
  return res.data
}

export async function updateDepartment(id, name) {
  const res = await apiClient.patch(`/organization/departments/${id}/`, { name })
  return res.data
}

export async function updateDesignation(id, title) {
  const res = await apiClient.patch(`/organization/designations/${id}/`, { title })
  return res.data
}

export async function updateEmployee(id, payload) {
  const res = await apiClient.patch(`/organization/employees/${id}/`, payload)
  return res.data
}

export async function getEmployeeRoles() {
  const res = await apiClient.get('/organization/employee-roles/')
  return res.data
}

export async function assignEmployeeRole(employeeId, roleId) {
  const res = await apiClient.post('/organization/employee-roles/', {
    employee: employeeId,
    role: roleId,
  })
  return res.data
}

export async function deleteEmployeeRole(id) {
  const res = await apiClient.delete(`/organization/employee-roles/${id}/`)
  return res.data
}