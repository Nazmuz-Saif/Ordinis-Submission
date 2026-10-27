import apiClient from './apiClient'
import { getAllPages, getPage } from './paging'

export async function getDepartments() {
  return getAllPages('/organization/departments/')
}

export async function createDepartment(name) {
  const res = await apiClient.post('/organization/departments/', { name })
  return res.data
}

export async function getDesignations() {
  return getAllPages('/organization/designations/')
}

export async function createDesignation(title) {
  const res = await apiClient.post('/organization/designations/', { title })
  return res.data
}

export async function getEmployeesPage(page = 1) {
  return getPage('/organization/employees/', { page })
}

export async function getEmployees() {
  return getAllPages('/organization/employees/')
}

export async function createEmployee(payload) {
  const res = await apiClient.post('/organization/employees/', payload)
  return res.data
}

// `head` is optional: an employee id, '' or null to clear it, undefined to leave it as it is.
export async function updateDepartment(id, name, head) {
  const payload = { name }
  if (head !== undefined) payload.head = head || null
  const res = await apiClient.patch(`/organization/departments/${id}/`, payload)
  return res.data
}

export async function getDepartmentOverview(id) {
  const res = await apiClient.get(`/organization/departments/${id}/overview/`)
  return res.data
}

export async function getDesignationOverview(id) {
  const res = await apiClient.get(`/organization/designations/${id}/overview/`)
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
  return getAllPages('/rbac/employee-roles/')
}

export async function assignEmployeeRole(employeeId, roleId) {
  const res = await apiClient.post('/rbac/employee-roles/', {
    employee: employeeId,
    role: roleId,
  })
  return res.data
}

export async function deleteEmployeeRole(id) {
  const res = await apiClient.delete(`/rbac/employee-roles/${id}/`)
  return res.data
}

export async function deleteDepartment(id) {
  const res = await apiClient.delete(`/organization/departments/${id}/`)
  return res.data
}

export async function deleteDesignation(id) {
  const res = await apiClient.delete(`/organization/designations/${id}/`)
  return res.data
}

export async function deleteEmployee(id) {
  const res = await apiClient.delete(`/organization/employees/${id}/`)
  return res.data
}

export async function getEmployee(id) {
  const res = await apiClient.get(`/organization/employees/${id}/`)
  return res.data
}

export async function getSubordinates(id) {
  return getAllPages(`/organization/employees/${id}/subordinates/`)
}

// The Roles a person holds and the Permissions they really have. Answers 403 for people who may not see it.
export async function getEmployeeAccess(id) {
  const res = await apiClient.get(`/organization/employees/${id}/access/`)
  return res.data
}
