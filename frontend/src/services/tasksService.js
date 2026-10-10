import apiClient from './apiClient'
import { getAllPages, getPage } from './paging'

export async function getTasksPage(page = 1) {
  return getPage('/tasks/tasks/', { page })
}

export async function getTasks() {
  return getAllPages('/tasks/tasks/')
}

export async function createTask(payload) {
  const res = await apiClient.post('/tasks/tasks/', payload)
  return res.data
}

export async function updateTask(id, payload) {
  const res = await apiClient.patch(`/tasks/tasks/${id}/`, payload)
  return res.data
}

export async function deleteTask(id) {
  const res = await apiClient.delete(`/tasks/tasks/${id}/`)
  return res.data
}

export async function startTask(id) {
  const res = await apiClient.post(`/tasks/tasks/${id}/start/`)
  return res.data
}

export async function submitTask(id) {
  const res = await apiClient.post(`/tasks/tasks/${id}/submit/`)
  return res.data
}
