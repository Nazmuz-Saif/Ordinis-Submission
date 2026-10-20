import { useEffect, useState } from 'react'
import { AlertTriangle, BarChart3, CheckCircle2, Gauge, Users } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getOverview } from '../../services/analyticsService'
import ChartCard from '../../components/common/ChartCard'
import EmptyState from '../../components/common/EmptyState'
import MetricCard from '../../components/common/MetricCard'
import { Notice, PageHeader } from '../admin/shared'
import { GroupedBarChartBox, LineChartBox } from '../dashboard/charts'
import { changeText } from './analyticsFormat'

function AnalyticsPage() {
  const { hasPermission } = useAuth()
  const allowed = hasPermission('view_analytics')
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!allowed) return
    getOverview()
      .then(setData)
      .catch((err) => setError(err?.response?.data?.error?.message || 'Could not load the analytics.'))
  }, [allowed])

  if (!allowed) {
    return (
      <EmptyState
        icon={BarChart3}
        title="You do not have access to this page"
        description="Seeing the company analytics needs the View Analytics permission."
      />
    )
  }

  const loading = !data && !error
  const metrics = data?.metrics
  const change = changeText(metrics?.attendance_rate_change)
  const months = data?.attendance_by_month || []
  const departments = data?.tasks_by_department || []
  const noAttendance = !months.some((m) => m.working_days > 0)

  return (
    <div data-testid="analytics-page" className="space-y-6">
      <PageHeader title="Analytics" subtitle="How healthy the company is: attendance and task completion, from your own data." />
      {error && <Notice>{error}</Notice>}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div data-testid="analytics-attendance-rate">
          <MetricCard
            loading={loading}
            label="Attendance rate (this month)"
            value={metrics ? `${metrics.attendance_rate}%` : ''}
            delta={change.text}
            deltaTone={change.tone}
            icon={Users}
          />
        </div>
        <div data-testid="analytics-completion-rate">
          <MetricCard
            loading={loading}
            label="Task completion rate"
            value={metrics ? `${metrics.task_completion_rate}%` : ''}
            icon={CheckCircle2}
          />
        </div>
        <div data-testid="analytics-overdue">
          <MetricCard loading={loading} label="Overdue tasks" value={metrics ? metrics.overdue_tasks : ''} icon={AlertTriangle} />
        </div>
        <div data-testid="analytics-workload">
          <MetricCard
            loading={loading}
            label="Average team workload"
            value={metrics ? metrics.average_workload : ''}
            delta={metrics ? 'open tasks per employee' : undefined}
            icon={Gauge}
          />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Attendance rate"
          subtitle="Last 6 months. A working day is a day when at least one employee checked in."
          loading={loading}
          empty={!!data && noAttendance}
          emptyText="No attendance recorded in the last 6 months."
        >
          <LineChartBox data={months} valueLabel="Attendance rate" />
        </ChartCard>
        <ChartCard
          title="Tasks by department"
          subtitle="Completed and pending tasks, by the department of the person they are assigned to."
          loading={loading}
          empty={!!data && departments.length === 0}
          emptyText="No tasks yet."
        >
          <GroupedBarChartBox data={departments} />
        </ChartCard>
      </div>
    </div>
  )
}

export default AnalyticsPage
