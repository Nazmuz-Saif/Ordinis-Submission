import apiClient from './apiClient'
import { getAllPages } from './paging'

export async function getToday() {
  const res = await apiClient.get('/attendance/attendance/today/')
  return res.data
}

export async function getRecords() {
  return getAllPages('/attendance/attendance/')
}

export async function checkIn() {
  const res = await apiClient.post('/attendance/attendance/check_in/')
  return res.data
}

export async function checkOut() {
  const res = await apiClient.post('/attendance/attendance/check_out/')
  return res.data
}

// One month of the logged-in employee's own attendance. month = "2026-10"; leave it out for this month.
export async function getCalendar(month) {
  const res = await apiClient.get('/attendance/attendance/calendar/', { params: month ? { month } : {} })
  return res.data
}
