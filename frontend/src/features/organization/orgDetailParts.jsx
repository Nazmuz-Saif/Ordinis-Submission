import { Link } from 'react-router-dom'
import { personName } from '../../utils/people'
import StatusPill from '../../components/common/StatusPill'

const TASK_STATUS = {
  in_progress: { label: 'In Progress', status: 'info' },
  submitted: { label: 'In Review', status: 'warning' },
  not_started: { label: 'To Do', status: 'neutral' },
  completed: { label: 'Done', status: 'success' },
}

export function PersonLink({ person, className = '' }) {
  if (!person) return <span className="text-[#71717A]">—</span>
  return (
    <Link to={`/organization/employees/${person.id}`} className={`text-[#6C31D6] hover:underline ${className}`}>
      {personName(person.full_name, person.user_email)}
    </Link>
  )
}

// The people table both detail pages share. `showDepartment` is for the Designation page.
export function MembersTable({ members, showDepartment = false, showDesignation = true }) {
  return (
    <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm overflow-x-auto">
      <table className="w-full text-sm" data-testid="members-table">
        <thead>
          <tr className="text-left text-xs text-[#71717A] border-b border-[#EEEEF2]">
            <th className="px-4 py-3 font-medium">Name</th>
            <th className="px-4 py-3 font-medium">Code</th>
            {showDesignation && <th className="px-4 py-3 font-medium">Designation</th>}
            {showDepartment && <th className="px-4 py-3 font-medium">Department</th>}
            <th className="px-4 py-3 font-medium">Reports to</th>
            <th className="px-4 py-3 font-medium text-right">Open tasks</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#EEEEF2]">
          {members.map((m) => (
            <tr key={m.id} data-testid="member-row" className="hover:bg-[#FAFAFA] transition-colors">
              <td className="px-4 py-3"><PersonLink person={m} className="font-medium" /></td>
              <td className="px-4 py-3 text-[#71717A]">{m.employee_code}</td>
              {showDesignation && <td className="px-4 py-3 text-[#14142B]">{m.designation_title || '—'}</td>}
              {showDepartment && <td className="px-4 py-3 text-[#14142B]">{m.department_name || '—'}</td>}
              <td className="px-4 py-3"><PersonLink person={m.manager} /></td>
              <td className="px-4 py-3 text-right text-[#14142B]">{m.open_tasks}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function TaskStatusPill({ status }) {
  const v = TASK_STATUS[status] || TASK_STATUS.not_started
  return <StatusPill status={v.status} label={v.label} />
}
