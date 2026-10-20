import { useEffect, useState } from 'react'
import { CalendarCheck, CalendarOff, ChevronLeft, ChevronRight, Palmtree, Percent } from 'lucide-react'
import { getCalendar } from '../../services/attendanceService'
import MetricCard from '../../components/common/MetricCard'
import { Notice } from '../admin/shared'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// Colour and text together: a day is never shown by colour alone.
const STATUS = {
  present: { label: 'Present', dot: 'bg-[#16A34A]' },
  absent: { label: 'Absent', dot: 'bg-[#DC2626]' },
  on_leave: { label: 'On Leave', dot: 'bg-[#F59E0B]' },
}

function dayNumber(isoDate) {
  return Number(isoDate.slice(8))
}

function AttendanceCalendar() {
  const [month, setMonth] = useState(undefined) // undefined = this month; then "2026-09" and so on
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getCalendar(month)
      .then((result) => {
        if (!active) return
        setData(result)
        setError('')
      })
      .catch((err) => {
        if (active) setError(err.response?.data?.error?.message || 'Could not load the calendar.')
      })
    return () => {
      active = false
    }
  }, [month])

  const summary = data?.summary
  const loading = !data && !error
  const blanks = data ? Array.from({ length: data.first_weekday }) : []

  return (
    <section data-testid="attendance-calendar" className="mb-6">
      <h2 className="text-lg font-semibold text-[#14142B] mb-3">Monthly calendar</h2>
      {error && <Notice>{error}</Notice>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 mb-4">
        <div data-testid="calendar-card-present">
          <MetricCard loading={loading} label="Present" value={summary ? summary.present : ''} icon={CalendarCheck} />
        </div>
        <div data-testid="calendar-card-absent">
          <MetricCard loading={loading} label="Absent" value={summary ? summary.absent : ''} icon={CalendarOff} />
        </div>
        <div data-testid="calendar-card-on-leave">
          <MetricCard loading={loading} label="On Leave" value={summary ? summary.on_leave : ''} icon={Palmtree} />
        </div>
        <div data-testid="calendar-card-rate">
          <MetricCard loading={loading} label="Attendance rate" value={summary ? `${summary.attendance_rate}%` : ''} icon={Percent} />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-5">
        <div className="flex items-center justify-between mb-4">
          <button
            type="button"
            onClick={() => data?.previous && setMonth(data.previous)}
            disabled={!data?.previous}
            data-testid="calendar-prev"
            aria-label="Previous month"
            className="rounded-lg border border-[#EEEEF2] p-2 text-[#14142B] hover:bg-[#EDE9FE] disabled:opacity-40 transition-colors duration-150"
          >
            <ChevronLeft size={18} />
          </button>
          <p data-testid="calendar-month-label" className="text-base font-semibold text-[#14142B]">
            {data ? data.label : ''}
          </p>
          <button
            type="button"
            onClick={() => data?.next && setMonth(data.next)}
            disabled={!data?.next}
            data-testid="calendar-next"
            aria-label="Next month"
            className="rounded-lg border border-[#EEEEF2] p-2 text-[#14142B] hover:bg-[#EDE9FE] disabled:opacity-40 transition-colors duration-150"
          >
            <ChevronRight size={18} />
          </button>
        </div>

        {loading ? (
          <div className="skeleton h-64 w-full rounded-lg" />
        ) : data ? (
          <div data-testid="calendar-grid" className="grid grid-cols-7 gap-1">
            {WEEKDAYS.map((name) => (
              <div key={name} className="text-center text-xs font-medium text-[#71717A] pb-2">{name}</div>
            ))}
            {blanks.map((_, index) => (
              <div key={`blank-${index}`} aria-hidden="true" />
            ))}
            {data.days.map((day) => {
              const status = day.status ? STATUS[day.status] : null
              return (
                <div
                  key={day.date}
                  data-testid={`calendar-day-${day.date}`}
                  data-status={day.status || 'none'}
                  title={status ? `${day.date}: ${status.label}` : day.date}
                  className="flex flex-col items-center justify-center rounded-lg py-2 text-sm text-[#14142B] hover:bg-[#FAFAFA] transition-colors duration-150"
                >
                  <span>{dayNumber(day.date)}</span>
                  <span className={`mt-1 h-2 w-2 rounded-full ${status ? status.dot : 'bg-transparent'}`} aria-hidden="true" />
                  {status && <span className="sr-only">{status.label}</span>}
                </div>
              )
            })}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-4 mt-4 text-xs text-[#71717A]">
          {Object.entries(STATUS).map(([key, item]) => (
            <span key={key} className="inline-flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-full ${item.dot}`} aria-hidden="true" />
              {item.label}
            </span>
          ))}
          <span>No dot: weekend, holiday, a day that is not over yet, or a future day.</span>
        </div>
      </div>
    </section>
  )
}

export default AttendanceCalendar
