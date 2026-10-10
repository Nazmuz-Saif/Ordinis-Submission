import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle, BadgeCheck, Building2, CalendarCheck, CheckSquare, ClipboardList, Clock,
  FileCheck2, Percent, UserCheck, UserMinus, Users, Wallet,
} from 'lucide-react'
import { getDashboardSummary } from '../../services/dashboardService'
import MetricCard from '../../components/common/MetricCard'
import ChartCard from '../../components/common/ChartCard'
import { BarChartBox, DonutChartBox } from './charts'

const STATUS_LABELS = {
  not_started: 'Not started',
  in_progress: 'In progress',
  submitted: 'Submitted',
  completed: 'Completed',
  rejected: 'Rejected',
}
const STATUS_COLORS = ['#A1A1AA', '#6C31D6', '#F59E0B', '#16A34A', '#DC2626']
const PRIORITY_LABELS = { low: 'Low', medium: 'Medium', high: 'High' }

const statusData = (counts) => Object.entries(STATUS_LABELS).map(([key, name]) => ({ name, value: counts[key] ?? 0 }))
const priorityData = (counts) => Object.entries(PRIORITY_LABELS).map(([key, name]) => ({ name, value: counts[key] ?? 0 }))
const hasAny = (data) => data.some((d) => d.value > 0)

function money(amount, currency) {
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount)
  } catch {
    return `${currency} ${Math.round(amount).toLocaleString('en-US')}`
  }
}

function Section({ id, title, subtitle, children }) {
  return (
    <section data-testid={`dashboard-section-${id}`} className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-[#14142B]">{title}</h2>
        <p className="text-sm text-[#71717A]">{subtitle}</p>
      </div>
      {children}
    </section>
  )
}

const CARDS = 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4'
const CHARTS = 'grid grid-cols-1 lg:grid-cols-2 gap-4'

function MeSection({ data, loading }) {
  const attendance = loading ? '' : data.checked_out_today ? 'Checked out' : data.checked_in_today ? 'Checked in' : 'Not yet'
  const status = loading ? [] : statusData(data.tasks_by_status)
  return (
    <Section id="me" title="My work" subtitle="Your tasks, attendance and approvals.">
      <div className={CARDS}>
        <MetricCard loading={loading} label="Open tasks" value={data?.open_tasks} icon={CheckSquare} />
        <MetricCard
          loading={loading} label="Overdue tasks" value={data?.overdue_tasks} icon={AlertTriangle}
          delta={data?.overdue_tasks > 0 ? 'Needs attention' : 'All on time'}
          deltaTone={data?.overdue_tasks > 0 ? 'negative' : 'positive'}
        />
        <MetricCard loading={loading} label="Attendance today" value={attendance} icon={CalendarCheck} />
        <MetricCard loading={loading} label="Approvals waiting for me" value={data?.approvals_waiting} icon={FileCheck2} />
      </div>
      <ChartCard title="My tasks by status" loading={loading} empty={!loading && !hasAny(status)} emptyText="No tasks assigned to you yet.">
        <BarChartBox data={status} colors={STATUS_COLORS} valueLabel="Tasks" />
      </ChartCard>
    </Section>
  )
}

function TeamSection({ data, loading }) {
  const status = loading ? [] : statusData(data.tasks_by_status)
  const priority = loading ? [] : priorityData(data.tasks_by_priority)
  return (
    <Section id="team" title="Team tasks" subtitle="All tasks in your company.">
      <div className={CARDS}>
        <MetricCard loading={loading} label="Total tasks" value={data?.total_tasks} icon={ClipboardList} />
        <MetricCard
          loading={loading} label="Overdue" value={data?.overdue_tasks} icon={AlertTriangle}
          delta={data?.overdue_tasks > 0 ? 'Past deadline' : 'None overdue'}
          deltaTone={data?.overdue_tasks > 0 ? 'negative' : 'positive'}
        />
        <MetricCard loading={loading} label="Awaiting review" value={data?.awaiting_review} icon={Clock} />
        <MetricCard loading={loading} label="Completion rate" value={loading ? '' : `${data.completion_rate}%`} icon={Percent} />
      </div>
      <div className={CHARTS}>
        <ChartCard title="Tasks by status" loading={loading} empty={!loading && !hasAny(status)} emptyText="No tasks in the company yet.">
          <DonutChartBox data={status.filter((d) => d.value > 0)} />
        </ChartCard>
        <ChartCard title="Tasks by priority" loading={loading} empty={!loading && !hasAny(priority)} emptyText="No tasks in the company yet.">
          <BarChartBox data={priority} valueLabel="Tasks" />
        </ChartCard>
      </div>
    </Section>
  )
}

function PeopleSection({ data, loading }) {
  const departments = loading ? [] : data.employees_by_department.map((d) => ({ name: d.name, value: d.count }))
  return (
    <Section id="people" title="People" subtitle="Headcount and attendance today.">
      <div className={CARDS}>
        <MetricCard
          loading={loading} label="Employees" value={data?.total_employees} icon={Users}
          delta={data?.new_this_month > 0 ? `+${data.new_this_month} this month` : 'No new this month'}
          deltaTone={data?.new_this_month > 0 ? 'positive' : 'neutral'}
        />
        <MetricCard loading={loading} label="Departments" value={data?.departments} icon={Building2} />
        <MetricCard loading={loading} label="Present today" value={data?.present_today} icon={UserCheck} />
        <MetricCard loading={loading} label="Attendance rate" value={loading ? '' : `${data.attendance_rate}%`} icon={BadgeCheck} />
      </div>
      <ChartCard title="Employees by department" loading={loading} empty={!loading && departments.length === 0} emptyText="No employees yet.">
        <BarChartBox data={departments} valueLabel="Employees" />
      </ChartCard>
    </Section>
  )
}

function FinanceSection({ data, loading }) {
  const payroll = loading ? [] : data.payroll_by_department.map((d) => ({ name: d.name, value: d.total }))
  const fmt = (v) => money(v, data?.currency || 'BDT')
  return (
    <Section id="finance" title="Finance" subtitle="Base pay from Salary Structures. Confidential.">
      <div className={CARDS}>
        <MetricCard loading={loading} label="Total base payroll / month" value={loading ? '' : fmt(data.total_base_payroll)} icon={Wallet} />
        <MetricCard loading={loading} label="Average base salary" value={loading ? '' : fmt(data.average_base_salary)} icon={Wallet} />
        <MetricCard loading={loading} label="Salary structures" value={data?.salary_structures} icon={FileCheck2} />
        <MetricCard
          loading={loading} label="Employees without salary" value={data?.employees_without_salary} icon={UserMinus}
          delta={data?.employees_without_salary > 0 ? 'Set up their pay' : 'Everyone is set up'}
          deltaTone={data?.employees_without_salary > 0 ? 'negative' : 'positive'}
        />
      </div>
      <ChartCard title="Base payroll by department" loading={loading} empty={!loading && payroll.length === 0} emptyText="No salary structures yet.">
        <BarChartBox data={payroll} valueLabel="Base payroll" formatValue={fmt} />
      </ChartCard>
    </Section>
  )
}

function DashboardPage() {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    getDashboardSummary()
      .then((data) => {
        if (active) setSummary(data)
      })
      .catch(() => {
        if (active) setError('Failed to load the dashboard.')
      })
    return () => {
      active = false
    }
  }, [attempt])

  const retry = useCallback(() => {
    setError('')
    setSummary(null)
    setAttempt((n) => n + 1)
  }, [])

  const loading = !summary && !error

  return (
    <div className="space-y-8">
      {error && (
        <div role="alert" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] px-4 py-3 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button type="button" onClick={retry} className="font-medium underline">Try again</button>
        </div>
      )}
      {(loading || summary?.me) && <MeSection data={summary?.me} loading={loading} />}
      {summary?.team && <TeamSection data={summary.team} loading={false} />}
      {summary?.people && <PeopleSection data={summary.people} loading={false} />}
      {summary?.finance && <FinanceSection data={summary.finance} loading={false} />}
    </div>
  )
}

export default DashboardPage
