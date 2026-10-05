import { useEffect, useState } from 'react'
import { CalendarCheck } from 'lucide-react'
import { checkIn, checkOut, getAttendance } from '../../services/attendanceService'

function AttendancePage() {
  const [attendance, setAttendance] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState('')

  const loadAttendance = async () => {
    try {
      setError('')
      const data = await getAttendance()
      const records = Array.isArray(data) ? data : data.results || []
      setAttendance(records[0] || null)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load attendance.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAttendance()
  }, [])

  const handleCheckIn = async () => {
    try {
      setActionLoading(true)
      setError('')
      const data = await checkIn()
      setAttendance(data)
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        'Failed to check in.'
      )
    } finally {
      setActionLoading(false)
    }
  }

  const handleCheckOut = async () => {
    try {
      setActionLoading(true)
      setError('')
      const data = await checkOut()
      setAttendance(data)
    } catch (err) {
      setError(
        err.response?.data?.error?.message ||
        err.response?.data?.message ||
        'Failed to check out.'
      )
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <p>Loading attendance...</p>
      </div>
    )
  }

  const checkedIn = Boolean(attendance?.check_in)
  const checkedOut = Boolean(attendance?.check_out)

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <CalendarCheck size={28} />
          <div>
            <h1 className="text-2xl font-semibold">Attendance</h1>
            <p className="text-sm text-gray-500">Today's attendance status</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="max-w-xl rounded-xl border bg-white p-6 shadow-sm">
        <div className="mb-6">
          <p className="text-sm text-gray-500">Date</p>
          <p className="mt-1 text-lg font-medium">
            {attendance?.date || new Date().toISOString().split('T')[0]}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="rounded-lg border p-4">
            <p className="text-sm text-gray-500">Check In</p>
            <p className="mt-2 font-medium">
              {attendance?.check_in
                ? new Date(attendance.check_in).toLocaleTimeString()
                : 'Not checked in'}
            </p>
          </div>

          <div className="rounded-lg border p-4">
            <p className="text-sm text-gray-500">Check Out</p>
            <p className="mt-2 font-medium">
              {attendance?.check_out
                ? new Date(attendance.check_out).toLocaleTimeString()
                : 'Not checked out'}
            </p>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleCheckIn}
            disabled={checkedIn || actionLoading}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {actionLoading ? 'Processing...' : 'Check In'}
          </button>

          <button
            type="button"
            onClick={handleCheckOut}
            disabled={!checkedIn || checkedOut || actionLoading}
            className="rounded-lg bg-gray-900 px-5 py-2.5 text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {actionLoading ? 'Processing...' : 'Check Out'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default AttendancePage
