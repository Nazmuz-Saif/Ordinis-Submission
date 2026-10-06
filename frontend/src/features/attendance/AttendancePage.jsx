
import { useEffect, useState } from 'react'
import {
  CalendarCheck,
  LogIn,
  LogOut,
  Clock3,
  Users,
  History,
} from 'lucide-react'
import {
  checkIn,
  checkOut,
  getAttendance,
  getAttendanceHistory,
} from '../../services/attendanceService'
import { getMe } from '../../services/authService'

function AttendancePage() {
  const [attendanceList, setAttendanceList] = useState([])
  const [historyList, setHistoryList] = useState([])
  const [myAttendance, setMyAttendance] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const loadAttendance = async () => {
    try {
      setLoading(true)
      setError('')

      const [
        attendanceData,
        userData,
        historyData,
      ] = await Promise.all([
        getAttendance(),
        getMe(),
        getAttendanceHistory(),
      ])

      const records = Array.isArray(attendanceData)
        ? attendanceData
        : attendanceData?.results || []

      const historyRecords = Array.isArray(historyData)
        ? historyData
        : historyData?.results || []

      const myEmployeeId =
        userData?.employee?.id ||
        userData?.employee_id

      const myRecord = records.find(
        (record) => record.employee === myEmployeeId
      )

      setAttendanceList(records)
      setHistoryList(historyRecords)
      setMyAttendance(myRecord || null)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.response?.data?.error?.message ||
        'Failed to load attendance.'
      )
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
      setSuccess('')

      const data = await checkIn()

      setMyAttendance(data)

      setAttendanceList((current) => {
        const exists = current.some(
          (record) => record.employee === data.employee
        )

        if (exists) {
          return current.map((record) =>
            record.employee === data.employee
              ? data
              : record
          )
        }

        return [...current, data]
      })

      setHistoryList((current) => {
        const exists = current.some(
          (record) => record.id === data.id
        )

        if (exists) {
          return current.map((record) =>
            record.id === data.id ? data : record
          )
        }

        return [data, ...current]
      })

      setSuccess('Check-in successful.')
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.response?.data?.error?.message ||
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
      setSuccess('')

      const data = await checkOut()

      setMyAttendance(data)

      setAttendanceList((current) => {
        const exists = current.some(
          (record) => record.employee === data.employee
        )

        if (exists) {
          return current.map((record) =>
            record.employee === data.employee
              ? data
              : record
          )
        }

        return [...current, data]
      })

      setHistoryList((current) => {
        const exists = current.some(
          (record) => record.id === data.id
        )

        if (exists) {
          return current.map((record) =>
            record.id === data.id ? data : record
          )
        }

        return [data, ...current]
      })

      setSuccess('Check-out successful.')
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.response?.data?.error?.message ||
        'Failed to check out.'
      )
    } finally {
      setActionLoading(false)
    }
  }

  const formatTime = (value) => {
    if (!value) {
      return '--'
    }

    return new Date(value).toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  const getStatus = (record) => {
    if (!record?.check_in) {
      return 'Not Checked In'
    }

    if (!record?.check_out) {
      return 'Checked In'
    }

    return 'Checked Out'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="mx-auto max-w-6xl">
          <div className="rounded-2xl border bg-white p-8 shadow-sm">
            <p className="text-gray-500">
              Loading attendance...
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-6xl">

        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-100 text-purple-600">
              <CalendarCheck size={25} />
            </div>

            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Attendance
              </h1>

              <p className="mt-1 text-sm text-gray-500">
                Manage and monitor attendance
              </p>
            </div>
          </div>

          <div className="hidden items-center gap-2 rounded-full bg-white px-4 py-2 text-sm text-gray-600 shadow-sm sm:flex">
            <Clock3 size={16} className="text-purple-600" />
            Attendance
          </div>
        </div>

        {error && (
          <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-5 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            {success}
          </div>
        )}

        <div className="mb-8 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-100">

          <div className="bg-gradient-to-r from-purple-600 to-purple-500 px-6 py-7 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-purple-100">
                  My Attendance
                </p>

                <h2 className="mt-1 text-2xl font-bold">
                  Today's Record
                </h2>
              </div>

              <div className="rounded-xl bg-white/15 p-3">
                <CalendarCheck size={28} />
              </div>
            </div>
          </div>

          <div className="p-6">

            <div className="mb-6 grid gap-4 sm:grid-cols-2">

              <div className="rounded-xl border border-gray-100 bg-gray-50 p-5">
                <div className="mb-3 flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
                    <LogIn size={18} />
                  </div>

                  <span className="text-sm font-medium text-gray-500">
                    Check In
                  </span>
                </div>

                <p className="text-2xl font-bold text-gray-900">
                  {formatTime(myAttendance?.check_in)}
                </p>

                <p className="mt-1 text-xs text-gray-400">
                  Today's check-in time
                </p>
              </div>

              <div className="rounded-xl border border-gray-100 bg-gray-50 p-5">
                <div className="mb-3 flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
                    <LogOut size={18} />
                  </div>

                  <span className="text-sm font-medium text-gray-500">
                    Check Out
                  </span>
                </div>

                <p className="text-2xl font-bold text-gray-900">
                  {formatTime(myAttendance?.check_out)}
                </p>

                <p className="mt-1 text-xs text-gray-400">
                  Today's check-out time
                </p>
              </div>

            </div>

            <div className="mb-6 flex items-center justify-between rounded-xl border border-purple-100 bg-purple-50 px-5 py-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                  Current Status
                </p>

                <p className="mt-1 text-lg font-semibold text-gray-900">
                  {getStatus(myAttendance)}
                </p>
              </div>

              <span className="rounded-full bg-purple-100 px-3 py-1.5 text-xs font-semibold text-purple-700">
                {myAttendance?.date || 'Today'}
              </span>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleCheckIn}
                disabled={actionLoading}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-purple-600 px-5 py-3 font-medium text-white shadow-sm transition hover:bg-purple-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
              >
                <LogIn size={19} />

                {actionLoading
                  ? 'Processing...'
                  : 'Check In'}
              </button>

              <button
                type="button"
                onClick={handleCheckOut}
                disabled={actionLoading}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-purple-600 px-5 py-3 font-medium text-white shadow-sm transition hover:bg-purple-700 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
              >
                <LogOut size={19} />

                {actionLoading
                  ? 'Processing...'
                  : 'Check Out'}
              </button>
            </div>

          </div>
        </div>

        {attendanceList.length > 1 && (
          <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-100">

            <div className="border-b px-6 py-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
                  <Users size={20} />
                </div>

                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    Today's Employee Attendance
                  </h2>

                  <p className="text-sm text-gray-500">
                    Attendance overview for your company
                  </p>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Employee
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Code
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Department
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Designation
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Check In
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Check Out
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Status
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {attendanceList.map((record) => (
                    <tr
                      key={record.employee}
                      className="border-t transition hover:bg-purple-50/40"
                    >
                      <td className="px-5 py-4 font-medium text-gray-900">
                        {record.employee_name}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {record.employee_code}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {record.department_name || '--'}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {record.designation_name || '--'}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {formatTime(record.check_in)}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {formatTime(record.check_out)}
                      </td>

                      <td className="px-5 py-4">
                        <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-700">
                          {getStatus(record)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

          </div>
        )}

        {historyList.length > 0 && (
          <div className="mt-8 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-100">

            <div className="border-b px-6 py-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
                  <History size={20} />
                </div>

                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    Attendance History
                  </h2>

                  <p className="text-sm text-gray-500">
                    Previous attendance records
                  </p>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Date
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Employee
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Code
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Department
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Designation
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Check In
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Check Out
                    </th>

                    <th className="px-5 py-4 font-semibold text-gray-600">
                      Status
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {historyList.map((record) => (
                    <tr
                      key={record.id}
                      className="border-t transition hover:bg-purple-50/40"
                    >
                      <td className="px-5 py-4 text-gray-600">
                        {record.date}
                      </td>

                      <td className="px-5 py-4 font-medium text-gray-900">
                        {record.employee_name}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {record.employee_code}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {record.department_name || '--'}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {record.designation_name || '--'}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {formatTime(record.check_in)}
                      </td>

                      <td className="px-5 py-4 text-gray-600">
                        {formatTime(record.check_out)}
                      </td>

                      <td className="px-5 py-4">
                        <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-700">
                          {getStatus(record)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

          </div>
        )}

      </div>
    </div>
  )
}

export default AttendancePage