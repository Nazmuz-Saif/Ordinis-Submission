import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Clock, CalendarCheck, ChevronDown, Search, Users } from 'lucide-react'
import { getTeamMonth, getTeamPeople } from '../../services/attendanceService'
import AttendanceCalendar from './AttendanceCalendar'
import MetricCard from '../../components/common/MetricCard'
import EmptyState from '../../components/common/EmptyState'
import useClickOutside from '../../hooks/useClickOutside'
import { personName } from '../../utils/people'

function EmployeePicker({ people, selected, onSelect }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const ref = useRef(null)
  useClickOutside(ref, () => setOpen(false))

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return people
    return people.filter((p) =>
      [p.full_name, p.user_email, p.employee_code, p.designation_title].some((v) => (v || '').toLowerCase().includes(q)),
    )
  }, [people, query])

  return (
    <div ref={ref} className="relative max-w-md">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        data-testid="team-employee-select"
        aria-haspopup="listbox"
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-2 bg-white border border-[#EEEEF2] rounded-lg px-3 py-2.5 text-sm text-left hover:border-[#6C31D6]/40 transition"
      >
        <span className={selected ? 'text-[#14142B] font-medium' : 'text-[#71717A]'}>
          {selected ? `${personName(selected.full_name, selected.user_email)} · ${selected.employee_code}` : 'Choose an employee…'}
        </span>
        <ChevronDown size={16} className="text-[#71717A]" />
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-[#EEEEF2] rounded-xl shadow-lg p-2">
          <div className="relative mb-2">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#71717A]" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, email or code"
              data-testid="team-employee-search"
              className="w-full border border-[#EEEEF2] rounded-lg pl-8 pr-3 py-2 text-sm outline-none focus:border-[#6C31D6]"
            />
          </div>
          <ul role="listbox" className="max-h-64 overflow-y-auto">
            {matches.length === 0 && <li className="px-3 py-2 text-sm text-[#71717A]">No one matches.</li>}
            {matches.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected?.id === p.id}
                  data-testid={`team-employee-option-${p.id}`}
                  onClick={() => { onSelect(p); setOpen(false); setQuery('') }}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-[#EDE9FE] transition-colors"
                >
                  <span className="block text-sm font-medium text-[#14142B]">{personName(p.full_name, p.user_email)}</span>
                  <span className="block text-xs text-[#71717A]">
                    {[p.employee_code, p.designation_title, p.department_name].filter(Boolean).join(' · ')}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function TeamAttendancePage() {
  const [people, setPeople] = useState(null)
  const [wholeCompany, setWholeCompany] = useState(false)
  const [selected, setSelected] = useState(null)
  const [month, setMonthData] = useState(null)      // the month the calendar is showing: records, hours
  const [error, setError] = useState('')

  useEffect(() => {
    getTeamPeople()
      .then((data) => {
        setPeople(data.results)
        setWholeCompany(data.whole_company)
      })
      .catch(() => setError('Could not load the people list.'))
  }, [])

  // A new function per person, so the calendar reloads for them (and goes back to this month).
  const fetcher = useCallback((m) => getTeamMonth(selected.id, m), [selected])

  return (
    <div className="pb-12">
      <h1 className="text-2xl font-bold text-[#14142B]">Team Attendance</h1>
      <p className="text-sm text-[#71717A] mt-1 mb-6">
        {wholeCompany ? 'Everyone in the company.' : 'The people below you in the hierarchy.'} Pick someone to see their month.
      </p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}

      {people === null && !error && <div className="skeleton h-10 w-80 rounded-lg" />}

      {people && people.length === 0 && (
        <EmptyState icon={Users} title="No team yet" description="Nobody reports to you, so there is no one to show here." />
      )}

      {people && people.length > 0 && (
        <>
          <div className="mb-6">
            <EmployeePicker people={people} selected={selected} onSelect={(p) => { setSelected(p); setMonthData(null) }} />
          </div>

          {!selected && (
            <EmptyState icon={CalendarCheck} title="Choose an employee" description="Their calendar, check-in and check-out times will appear here." />
          )}

          {selected && (
            <div data-testid="team-attendance-view">
              <p className="text-base font-semibold text-[#14142B] mb-3" data-testid="team-selected-name">
                {personName(selected.full_name, selected.user_email)}
                <span className="text-sm font-normal text-[#71717A]"> · {selected.designation_title || 'No designation'}</span>
              </p>

              <div className="grid gap-4 sm:grid-cols-2 mb-4">
                <div data-testid="team-card-days">
                  <MetricCard loading={!month} label="Days present" value={month ? month.days_present : ''} icon={CalendarCheck} />
                </div>
                <div data-testid="team-card-hours">
                  <MetricCard loading={!month} label="Total hours" value={month ? `${month.total_hours} h` : ''} icon={Clock} />
                </div>
              </div>

              <AttendanceCalendar key={selected.id} fetcher={fetcher} onData={setMonthData} title={null} />

              <section className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-hidden" data-testid="team-day-table">
                <h2 className="text-base font-semibold text-[#14142B] px-5 pt-4 pb-3">Days worked</h2>
                {month && month.records.length === 0 ? (
                  <p className="px-5 pb-5 text-sm text-[#71717A]">No check-ins in {month.label}.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-[#71717A] border-y border-[#EEEEF2] bg-[#FAFAFA]">
                          <th className="px-5 py-2 font-medium">Date</th>
                          <th className="px-5 py-2 font-medium">Check-in</th>
                          <th className="px-5 py-2 font-medium">Check-out</th>
                          <th className="px-5 py-2 font-medium text-right">Hours</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#EEEEF2]">
                        {(month?.records || []).map((r) => (
                          <tr key={r.date} data-testid={`team-row-${r.date}`}>
                            <td className="px-5 py-2.5 text-[#14142B]">{r.date}</td>
                            <td className="px-5 py-2.5">{r.check_in_time}</td>
                            <td className="px-5 py-2.5 text-[#71717A]">{r.check_out_time || 'No check-out'}</td>
                            <td className="px-5 py-2.5 text-right">{r.hours === null ? '—' : r.hours}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default TeamAttendancePage
