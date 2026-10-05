import apiClient from './apiClient'

export async function getAttendance() {
  const response = await apiClient.get('/attendance/attendance/')
  return response.data
}

export async function checkIn() {
  const response = await apiClient.post('/attendance/attendance/check-in/')
  return response.data
}

export async function checkOut() {
  const response = await apiClient.post('/attendance/attendance/check-out/')
  return response.data
}
