
import apiClient from './apiClient'

export async function getAttendance() {
  const response = await apiClient.get('/attendance/attendance/')
  return response.data
}

export async function getAttendanceHistory() {
  const response = await apiClient.get(
    '/attendance/attendance/history/'
  )
  return response.data
}

export async function checkIn() {
  const response = await apiClient.post(
    '/attendance/attendance/check_in/'
  )
  return response.data
}

export async function checkOut() {
  const response = await apiClient.post(
    '/attendance/attendance/check_out/'
  )
  return response.data
}
