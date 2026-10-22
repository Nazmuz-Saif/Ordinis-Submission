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

// Team Attendance: the people I may open (everyone with view_team_attendance, otherwise my team).
export async function getTeamPeople() {
  const res = await apiClient.get('/attendance/attendance/team/people/')
  return res.data
}

// One person's month with check-in, check-out and hours. month = "2026-10"; leave it out for this month.
export async function getTeamMonth(employeeId, month) {
  const res = await apiClient.get('/attendance/attendance/team/', { params: { employee: employeeId, ...(month ? { month } : {}) } })
  return res.data
}
