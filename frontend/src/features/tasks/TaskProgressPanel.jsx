import { useEffect, useState } from 'react'
import { ExternalLink, Flag, X } from 'lucide-react'
import { addProgress, getProgressPage } from '../../services/tasksService'
import Pagination from '../../components/common/Pagination'
import EmptyState from '../../components/common/EmptyState'

const formatDay = (value) => new Date(value + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
const isWebLink = (value) => /^https?:\/\//i.test(value || '')
const errorMessage = (err) => {
  const e = err.response?.data?.error
  const first = e?.field_errors && Object.values(e.field_errors)[0]
  return (Array.isArray(first) ? first[0] : first) || e?.message || 'Could not save your progress.'
}

const EMPTY_FORM = { update_text: '', progress_percent: 0, blocker_text: '', external_reference_url: '' }

// Side panel on a Kanban card: the progress timeline, and (for the assignee only) the form for today's note.
function TaskProgressPanel({ card, onClose, onChanged }) {
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [form, setForm] = useState({ ...EMPTY_FORM, progress_percent: card.progress_percent })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getProgressPage(card.id, page)
      .then((result) => {
        if (!active) return
        setData(result)
        setLoadError('')
      })
      .catch(() => {
        if (active) setLoadError('Failed to load the timeline.')
      })
    return () => {
      active = false
    }
  }, [card.id, page, refresh])

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await addProgress(card.id, {
        update_text: form.update_text,
        progress_percent: Number(form.progress_percent),
        blocker_text: form.blocker_text,
        external_reference_url: form.external_reference_url,
      })
      setForm({ ...EMPTY_FORM, progress_percent: form.progress_percent })
      setPage(1)
      setRefresh((n) => n + 1)
      onChanged()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const input = 'mt-1 w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#6C31D6]/30'

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-[#14142B]/40">
      <aside data-testid="progress-panel" role="dialog" aria-label="Task progress" className="bg-white w-full max-w-lg h-full overflow-y-auto shadow-xl p-5 space-y-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-[#14142B]">{card.title}</h2>
            <p className="text-sm text-[#71717A]">{card.assigned_to_email}</p>
          </div>
          <button type="button" aria-label="Close" onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#FAFAFA]">
            <X size={18} />
          </button>
        </div>

        {card.can_add_progress ? (
          <form data-testid="progress-form" onSubmit={submit} className="space-y-3 rounded-xl border border-[#EEEEF2] p-4">
            <h3 className="font-medium text-[#14142B]">Add today&apos;s progress</h3>
            <label className="block text-sm text-[#14142B]">
              What did you do?
              <textarea
                data-testid="progress-text" required rows={3} maxLength={1000} value={form.update_text} onChange={set('update_text')}
                className={input}
              />
            </label>
            <label className="block text-sm text-[#14142B]">
              Progress: {form.progress_percent}%
              <input
                data-testid="progress-percent" type="range" min={0} max={100} step={5} value={form.progress_percent}
                onChange={set('progress_percent')} className="w-full accent-[#6C31D6]"
              />
            </label>
            <label className="block text-sm text-[#14142B]">
              Blocker (optional)
              <input data-testid="progress-blocker" maxLength={500} value={form.blocker_text} onChange={set('blocker_text')} className={input} />
            </label>
            <label className="block text-sm text-[#14142B]">
              Link, for example a GitHub commit (optional)
              <input
                data-testid="progress-link" type="url" placeholder="https://" maxLength={500}
                value={form.external_reference_url} onChange={set('external_reference_url')} className={input}
              />
            </label>
            <p className="text-xs text-[#71717A]">Text only. Files and code are never uploaded.</p>
            {error && <p data-testid="progress-error" role="alert" className="text-sm text-[#DC2626]">{error}</p>}
            <button
              type="submit" data-testid="progress-submit" disabled={saving}
              className="bg-[#6C31D6] hover:bg-[#5B27B8] text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60 transition-colors duration-150"
            >
              {saving ? 'Saving...' : 'Add progress'}
            </button>
          </form>
        ) : (
          <p data-testid="progress-readonly-note" className="rounded-lg bg-[#FAFAFA] border border-[#EEEEF2] px-4 py-3 text-sm text-[#71717A]">
            {card.status === 'completed'
              ? 'This task is completed, so no more progress can be added.'
              : 'Only the assignee can add progress.'}
          </p>
        )}

        <div>
          <h3 className="font-medium text-[#14142B] mb-3">Timeline</h3>
          {loadError && <p role="alert" className="text-sm text-[#DC2626]">{loadError}</p>}
          {!data && !loadError && <div className="skeleton h-24 w-full rounded-xl" />}
          {data && data.items.length === 0 && (
            <EmptyState title="No progress yet" description="Daily notes from the assignee appear here." />
          )}
          {data && data.items.length > 0 && (
            <ol className="space-y-3 border-l-2 border-[#EEEEF2] pl-4">
              {data.items.map((entry) => (
                <li key={entry.id} data-testid="progress-entry" className="relative">
                  <span className="absolute -left-[22px] top-1.5 h-2.5 w-2.5 rounded-full bg-[#6C31D6]" />
                  <div className="flex items-center justify-between text-xs text-[#71717A]">
                    <span>{formatDay(entry.date)} · {entry.employee_email}</span>
                    <span className="font-medium text-[#6C31D6]">{entry.progress_percent}%</span>
                  </div>
                  <p className="text-sm text-[#14142B] mt-1 whitespace-pre-wrap">{entry.update_text}</p>
                  {entry.blocker_text && (
                    <p className="flex items-center gap-1.5 text-xs text-[#B45309] mt-1">
                      <Flag size={12} /> Blocker: {entry.blocker_text}
                    </p>
                  )}
                  {isWebLink(entry.external_reference_url) && (
                    <a
                      href={entry.external_reference_url} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-[#6C31D6] hover:underline mt-1 break-all"
                    >
                      <ExternalLink size={12} /> {entry.external_reference_url}
                    </a>
                  )}
                </li>
              ))}
            </ol>
          )}
          {data && (
            <Pagination page={page} totalPages={data.totalPages} count={data.count} pageSize={data.pageSize} onChange={setPage} />
          )}
        </div>
      </aside>
    </div>
  )
}

export default TaskProgressPanel
