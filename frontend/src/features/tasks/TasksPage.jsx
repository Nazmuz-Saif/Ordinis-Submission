import { useEffect, useState } from 'react'
import { CalendarDays, CheckSquare, Pencil, Plus, Trash2 } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { getEmployees } from '../../services/organizationService'
import {
  getTasksPage, createTask, updateTask, deleteTask, startTask, submitTask,
} from '../../services/tasksService'
import StatusPill from '../../components/common/StatusPill'
import EmptyState from '../../components/common/EmptyState'
import Pagination from '../../components/common/Pagination'

const STATUS = {
  not_started: { status: 'neutral', label: 'Not Started' },
  in_progress: { status: 'info', label: 'In Progress' },
  submitted: { status: 'warning', label: 'Submitted' },
  completed: { status: 'success', label: 'Completed' },
  rejected: { status: 'failed', label: 'Rejected' },
}

const PRIORITY = {
  high: { label: 'High', className: 'bg-[#DC2626]/10 text-[#B91C1C]' },
  medium: { label: 'Medium', className: 'bg-[#F59E0B]/10 text-[#B45309]' },
  low: { label: 'Low', className: 'bg-[#71717A]/10 text-[#52525B]' },
}

const EMPTY_FORM = { title: '', description: '', assigned_to: '', priority: 'medium', deadline: '' }

const inputClass =
  'w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] focus:ring-2 focus:ring-[#6C31D6]/15 transition'

function errorMessage(err, fallback) {
  return err.response?.data?.error?.message || fallback
}

function employeeLabel(emp) {
  return `${emp.user_email} · ${emp.employee_code}`
}

function isOverdue(task) {
  if (!task.deadline || task.status === 'completed') return false
  return task.deadline < new Date().toISOString().slice(0, 10)
}

function TasksPage() {
  const { me, hasPermission } = useAuth()
  const canManage = hasPermission('create_task')

  const [tasks, setTasks] = useState([])
  const [page, setPage] = useState(1)
  const [pageInfo, setPageInfo] = useState({ count: 0, pageSize: 20, totalPages: 1 })
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  // form modal: null = closed, {} = create, {id,...} = edit
  const [form, setForm] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  async function reload() {
    try {
      const data = await getTasksPage(page)
      setTasks(data.items)
      setPageInfo(data)
    } catch (err) {
      if (err.response?.status === 404 && page > 1) {
        setPage(page - 1) // the last item of the last page is gone
        return
      }
      setError(errorMessage(err, 'Failed to load tasks.'))
    }
  }

  useEffect(() => {
    let active = true
    getTasksPage(page)
      .then((data) => {
        if (!active) return
        setTasks(data.items)
        setPageInfo(data)
      })
      .catch((err) => {
        if (!active) return
        if (err.response?.status === 404 && page > 1) setPage(page - 1)
        else setError(errorMessage(err, 'Failed to load tasks.'))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [page])

  useEffect(() => {
    if (!canManage) return
    getEmployees()
      .then(setEmployees)
      .catch((err) => setError(errorMessage(err, 'Failed to load employees.')))
  }, [canManage])

  async function run(action, successText, failText) {
    setError('')
    setMessage('')
    try {
      await action()
      setMessage(successText)
      await reload()
    } catch (err) {
      setError(errorMessage(err, failText))
    }
  }

  function openCreate() {
    setEditingId(null)
    setForm({ ...EMPTY_FORM })
    setFormError('')
  }

  function openEdit(task) {
    setEditingId(task.id)
    setForm({
      title: task.title,
      description: task.description || '',
      assigned_to: task.assigned_to,
      priority: task.priority,
      deadline: task.deadline || '',
    })
    setFormError('')
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setFormError('')
    const payload = { ...form, deadline: form.deadline || null }
    try {
      if (editingId) await updateTask(editingId, payload)
      else await createTask(payload)
      setForm(null)
      setMessage(editingId ? 'Task updated.' : 'Task created.')
      await reload()
    } catch (err) {
      setFormError(errorMessage(err, 'Failed to save the task.'))
    } finally {
      setSaving(false)
    }
  }

  function handleDelete(task) {
    if (!confirm(`Delete the task "${task.title}"?`)) return
    run(() => deleteTask(task.id), 'Task deleted.', 'Failed to delete the task.')
  }

  const setField = (name) => (e) => setForm((prev) => ({ ...prev, [name]: e.target.value }))

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-1">
        <h1 className="text-2xl font-bold text-[#14142B]">Tasks</h1>
        {canManage && (
          <button
            onClick={openCreate}
            data-testid="new-task-button"
            className="ml-auto flex items-center gap-1.5 bg-[#6C31D6] hover:bg-[#5A28B0] active:scale-[0.98] text-white rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150"
          >
            <Plus size={16} /> New Task
          </button>
        )}
      </div>
      <p className="text-sm text-[#71717A] mb-5">
        {canManage ? 'All tasks in your company.' : 'Tasks assigned to you, and tasks you created.'}
      </p>

      {error && <p className="text-sm text-[#DC2626] mb-4">{error}</p>}
      {message && <p className="text-sm text-[#16A34A] mb-4">{message}</p>}

      {loading ? (
        <p className="text-sm text-[#71717A]">Loading...</p>
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={CheckSquare}
          title="No tasks yet"
          description={canManage ? 'Create the first task and assign it to someone.' : 'Nothing has been assigned to you yet.'}
          actionLabel={canManage ? 'New Task' : undefined}
          onAction={canManage ? openCreate : undefined}
        />
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[#71717A] border-b border-[#EEEEF2]">
                <th className="px-4 py-3 font-medium">Task</th>
                <th className="px-4 py-3 font-medium">Assignee</th>
                <th className="px-4 py-3 font-medium">Priority</th>
                <th className="px-4 py-3 font-medium">Deadline</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EEEEF2]">
              {tasks.map((task) => {
                const isAssignee = me?.employee_id === task.assigned_to
                const status = STATUS[task.status]
                const priority = PRIORITY[task.priority]
                return (
                  <tr key={task.id} data-testid="task-row" className="hover:bg-[#FAFAFA] transition-colors duration-150">
                    <td className="px-4 py-3 max-w-xs">
                      <p className="font-medium text-[#14142B]">{task.title}</p>
                      {task.description && <p className="text-xs text-[#71717A] truncate">{task.description}</p>}
                    </td>
                    <td className="px-4 py-3 text-[#14142B]">{task.assigned_to_email}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${priority.className}`}>
                        {priority.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {task.deadline ? (
                        <span className={`inline-flex items-center gap-1 ${isOverdue(task) ? 'text-[#DC2626]' : 'text-[#14142B]'}`}>
                          <CalendarDays size={13} aria-hidden="true" />
                          {task.deadline}
                          {isOverdue(task) && <span className="text-xs">(overdue)</span>}
                        </span>
                      ) : (
                        <span className="text-[#71717A]">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={status.status} label={status.label} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1.5">
                        {isAssignee && (task.status === 'not_started' || task.status === 'rejected') && (
                          <button
                            onClick={() => run(() => startTask(task.id), 'Task started.', 'Failed to start the task.')}
                            data-testid="start-task"
                            className="border border-[#6C31D6] text-[#6C31D6] hover:bg-[#EDE9FE] rounded-lg px-3 py-1 text-xs font-medium transition-colors"
                          >
                            Start
                          </button>
                        )}
                        {isAssignee && task.status === 'in_progress' && (
                          <button
                            onClick={() => run(() => submitTask(task.id), 'Task submitted for review.', 'Failed to submit the task.')}
                            data-testid="submit-task"
                            className="bg-[#6C31D6] hover:bg-[#5A28B0] text-white rounded-lg px-3 py-1 text-xs font-medium transition-colors"
                          >
                            Submit
                          </button>
                        )}
                        {canManage && task.status === 'submitted' && (
                          <>
                            <button
                              onClick={() => run(() => updateTask(task.id, { status: 'completed' }), 'Task marked completed.', 'Failed to update the task.')}
                              data-testid="complete-task"
                              className="bg-[#16A34A] hover:bg-[#15803D] text-white rounded-lg px-3 py-1 text-xs font-medium transition-colors"
                            >
                              Complete
                            </button>
                            <button
                              onClick={() => run(() => updateTask(task.id, { status: 'rejected' }), 'Task sent back.', 'Failed to update the task.')}
                              data-testid="reject-task"
                              className="border border-[#DC2626] text-[#DC2626] hover:bg-[#DC2626]/5 rounded-lg px-3 py-1 text-xs font-medium transition-colors"
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {canManage && (
                          <>
                            <button
                              onClick={() => openEdit(task)}
                              title="Edit task"
                              data-testid="edit-task"
                              className="p-1.5 rounded-lg text-[#71717A] hover:bg-[#FAFAFA] hover:text-[#6C31D6] transition-colors"
                            >
                              <Pencil size={15} />
                            </button>
                            <button
                              onClick={() => handleDelete(task)}
                              title="Delete task"
                              data-testid="delete-task"
                              className="p-1.5 rounded-lg text-[#71717A] hover:bg-[#FAFAFA] hover:text-[#DC2626] transition-colors"
                            >
                              <Trash2 size={15} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <Pagination
        page={page}
        totalPages={pageInfo.totalPages}
        count={pageInfo.count}
        pageSize={pageInfo.pageSize}
        onChange={setPage}
      />

      {form && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#14142B]/40 p-4">
          <form onSubmit={handleSave} data-testid="task-form" className="bg-white rounded-xl shadow-xl w-full max-w-lg p-5">
            <h2 className="text-lg font-semibold text-[#14142B] mb-4">{editingId ? 'Edit task' : 'New task'}</h2>

            <label className="block text-sm font-medium text-[#14142B] mb-1">Title</label>
            <input
              value={form.title}
              onChange={setField('title')}
              required
              data-testid="task-title"
              className={`${inputClass} mb-3`}
            />

            <label className="block text-sm font-medium text-[#14142B] mb-1">Description (optional)</label>
            <textarea value={form.description} onChange={setField('description')} rows={3} className={`${inputClass} mb-3`} />

            <label className="block text-sm font-medium text-[#14142B] mb-1">Assign to</label>
            <select
              value={form.assigned_to}
              onChange={setField('assigned_to')}
              required
              data-testid="task-assignee"
              className={`${inputClass} mb-3`}
            >
              <option value="">Choose an employee...</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>{employeeLabel(emp)}</option>
              ))}
            </select>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-[#14142B] mb-1">Priority</label>
                <select value={form.priority} onChange={setField('priority')} data-testid="task-priority" className={inputClass}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#14142B] mb-1">Deadline</label>
                <input type="date" value={form.deadline} onChange={setField('deadline')} data-testid="task-deadline" className={inputClass} />
              </div>
            </div>

            {formError && <p className="text-sm text-[#DC2626] mt-3">{formError}</p>}

            <div className="flex justify-end gap-2 mt-5">
              <button type="button" onClick={() => setForm(null)} className="px-4 py-2 text-sm text-[#71717A] hover:text-[#14142B]">
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                data-testid="task-save"
                className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              >
                {editingId ? 'Save changes' : 'Create task'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

export default TasksPage
