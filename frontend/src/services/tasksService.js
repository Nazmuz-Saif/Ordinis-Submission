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

// ---- Kanban board and daily progress (ST-125) ----
export async function getBoard() {
  const res = await apiClient.get('/tasks/tasks/board/')
  return res.data // { columns: [{ key, label, count, has_more, cards: [...] }] }
}

// column: 'todo' | 'in_progress' | 'review' | 'done'. The server decides if the move is allowed.
export async function moveTask(id, column) {
  const res = await apiClient.post(`/tasks/tasks/${id}/move/`, { column })
  return res.data
}

export async function getProgressPage(id, page = 1) {
  return getPage(`/tasks/tasks/${id}/progress/`, { page })
}

// payload: { update_text, progress_percent, blocker_text?, external_reference_url? }. Text only: no files.
export async function addProgress(id, payload) {
  const res = await apiClient.post(`/tasks/tasks/${id}/progress/`, payload)
  return res.data
}
