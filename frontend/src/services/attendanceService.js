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
