import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Building2, CheckCircle2, ListChecks, Lock, Users } from 'lucide-react'
import MetricCard from '../../components/common/MetricCard'
import EmptyState from '../../components/common/EmptyState'
import { getDepartmentOverview } from '../../services/organizationService'
import { MembersTable, PersonLink, TaskStatusPill } from './orgDetailParts'

function formatDate(value) {
  if (!value) return '—'
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

function DepartmentDetailPage() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getDepartmentOverview(id)
      .then((res) => { if (!cancelled) setData(res) })
      .catch((err) => { if (!cancelled) setError(err.response?.status === 404 ? 'This department was not found.' : 'Failed to load this department.') })
    return () => { cancelled = true }
  }, [id])

  const back = (
    <Link to="/organization" className="inline-flex items-center gap-1 text-sm text-[#71717A] hover:text-[#6C31D6] mb-4">
      <ArrowLeft size={14} /> Departments
    </Link>
  )

  if (error) return <div>{back}<p className="text-sm text-[#DC2626]" data-testid="detail-error">{error}</p></div>
  if (!data) return <div>{back}<p className="text-sm text-[#71717A]">Loading...</p></div>

  const s = data.task_summary
  const running = data.running_tasks
  return (
    <div>
      {back}
      <div className="flex items-start gap-3 mb-6">
        <div className="w-11 h-11 rounded-xl bg-[#6C31D6]/10 text-[#6C31D6] flex items-center justify-center shrink-0">
          <Building2 size={22} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[#14142B]" data-testid="department-name">{data.name}</h1>
          <p className="text-sm text-[#71717A] mt-1" data-testid="department-head-line">
            Head: {data.head ? <PersonLink person={data.head} /> : 'not set'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard label="People" value={data.member_count} icon={Users} />
        <MetricCard label="Running tasks" value={s.in_progress + s.submitted} icon={ListChecks} />
        <MetricCard label="Completed" value={s.completed} icon={CheckCircle2} />
        <MetricCard label="Overdue" value={s.overdue} icon={AlertTriangle} delta={s.overdue ? 'Needs attention' : undefined} deltaTone="negative" />
      </div>

      <h2 className="text-base font-semibold text-[#14142B] mb-3">Running tasks</h2>
      {running.length > 0 && (
        <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm divide-y divide-[#EEEEF2] mb-3" data-testid="running-tasks">
          {running.map((t) => (
            <div key={t.id} data-testid="running-task" className="px-4 py-3 flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="flex-1 min-w-[160px] text-sm font-medium text-[#14142B]">{t.title}</span>
              <span className="text-sm"><PersonLink person={t.assignee} /></span>
              <TaskStatusPill status={t.status} />
              <span className="text-xs text-[#71717A] w-28">Due {formatDate(t.deadline)}</span>
              <span className="flex items-center gap-2 w-28" aria-label={`Progress ${t.progress_percent}%`}>
                <span className="flex-1 h-1.5 rounded-full bg-[#EEEEF2] overflow-hidden">
                  <span className="block h-full bg-[#6C31D6]" style={{ width: `${t.progress_percent}%` }} />
                </span>
                <span className="text-xs text-[#71717A]">{t.progress_percent}%</span>
              </span>
            </div>
          ))}
        </div>
      )}
      {data.hidden_running_tasks > 0 && (
        <p className="flex items-center gap-1.5 text-xs text-[#71717A] mb-3" data-testid="hidden-tasks-note">
          <Lock size={12} aria-hidden="true" />
          {data.hidden_running_tasks} more running {data.hidden_running_tasks === 1 ? 'task is' : 'tasks are'} not shown: only the person, their managers and task managers can see them.
        </p>
      )}
      {running.length === 0 && data.hidden_running_tasks === 0 && (
        <div className="mb-3"><EmptyState title="No running tasks" description="Nobody in this department has a task in progress right now." /></div>
      )}

      <h2 className="text-base font-semibold text-[#14142B] mt-8 mb-3">People</h2>
      {data.members.length === 0
        ? <EmptyState icon={Users} title="No people yet" description="Assign employees to this department from the Employees page." />
        : <MembersTable members={data.members} />}
    </div>
  )
}

export default DepartmentDetailPage
