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