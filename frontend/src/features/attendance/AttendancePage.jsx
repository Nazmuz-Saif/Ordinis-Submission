import { useEffect, useState } from 'react'
import { CalendarCheck, LogIn, LogOut } from 'lucide-react'
import { getToday, getRecords, checkIn, checkOut } from '../../services/attendanceService'
import StatusPill from '../../components/common/StatusPill'
import EmptyState from '../../components/common/EmptyState'

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

function formatDay(isoDate) {
  // "2026-10-05" -> "Monday, 5 October 2026" (parsed as a plain calendar date, no time zone shift)
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })
}

function statusOf(record) {
  if (!record) return { pill: 'neutral', pillLabel: 'Not checked in', text: 'You have not checked in yet today.' }
  if (record.check_out_time) {
    return { pill: 'success', pillLabel: 'Checked out', text: `Checked out at ${record.check_out_time}.` }
  }
  return { pill: 'info', pillLabel: 'Checked in', text: `Checked in at ${record.check_in_time}.` }
}

function AttendancePage() {
  const [today, setToday] = useState(null) // { date, record }
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function reload() {
    try {
      const [todayData, recordData] = await Promise.all([getToday(), getRecords()])
      setToday(todayData)
      setRecords(recordData)
    } catch (err) {
      setError(errorMessage(err, 'Failed to load attendance.'))
    }
  }

  useEffect(() => {
    let active = true
    Promise.all([getToday(), getRecords()])
      .then(([todayData, recordData]) => {
        if (!active) return
        setToday(todayData)
        setRecords(recordData)
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, 'Failed to load attendance.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  async function run(action, successText, failText) {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await action()
      setMessage(successText)
    } catch (err) {
      setError(errorMessage(err, failText))
    }
    await reload()
    setBusy(false)
  }

  const record = today?.record || null
  const status = statusOf(record)

  return (
    <div>
      <h1 className="text-2xl font-bold text-[#14142B]">Attendance</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-5">One check-in and one check-out per day, in your company's local time.</p>

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : (
        <>
          <div data-testid="attendance-today" className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-5 mb-6">
            <p className="text-xs text-[#71717A]">Today</p>
            <p data-testid="attendance-date" className="text-lg font-semibold text-[#14142B]">
              {today ? formatDay(today.date) : ''}
            </p>

            <div className="flex flex-wrap items-center gap-3 mt-3">
              <span data-testid="attendance-status">
                <StatusPill status={status.pill} label={status.pillLabel} />
              </span>
              <span data-testid="attendance-status-text" className="text-sm text-[#14142B]">{status.text}</span>
            </div>

            <div className="flex flex-wrap gap-3 mt-5">
              <button
                onClick={() => run(checkIn, 'Checked in.', 'Check-in failed.')}
                disabled={busy}
                data-testid="check-in-button"
                className="flex items-center gap-2 bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 active:scale-[0.98] text-white rounded-lg px-6 py-3 text-sm font-medium transition-all duration-150"
              >
                <LogIn size={17} /> Check In
              </button>
              <button
                onClick={() => run(checkOut, 'Checked out.', 'Check-out failed.')}
                disabled={busy}
                data-testid="check-out-button"
                className="flex items-center gap-2 border border-[#6C31D6] text-[#6C31D6] hover:bg-[#EDE9FE] disabled:opacity-60 active:scale-[0.98] rounded-lg px-6 py-3 text-sm font-medium transition-all duration-150"
              >
                <LogOut size={17} /> Check Out
              </button>
            </div>

            {error && <p data-testid="attendance-error" className="text-sm text-[#DC2626] mt-4">{error}</p>}
            {message && <p data-testid="attendance-message" className="text-sm text-[#16A34A] mt-4">{message}</p>}
          </div>

          <h2 className="text-lg font-semibold text-[#14142B] mb-3">My attendance</h2>
          {records.length === 0 ? (
            <EmptyState
              icon={CalendarCheck}
              title="No attendance yet"
              description="Your check-ins will be listed here."
            />
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-[#71717A] border-b border-[#EEEEF2]">
                    <th className="px-4 py-3 font-medium">Date</th>
                    <th className="px-4 py-3 font-medium">Check in</th>
                    <th className="px-4 py-3 font-medium">Check out</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EEEEF2]">
                  {records.map((r) => {
                    const s = statusOf(r)
                    return (
                      <tr key={r.id} data-testid="attendance-row" className="hover:bg-[#FAFAFA] transition-colors duration-150">
                        <td className="px-4 py-3 text-[#14142B]">{r.date}</td>
                        <td className="px-4 py-3 text-[#14142B]">{r.check_in_time}</td>
                        <td className="px-4 py-3 text-[#14142B]">{r.check_out_time || '-'}</td>
                        <td className="px-4 py-3"><StatusPill status={s.pill} label={s.pillLabel} /></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default AttendancePage
