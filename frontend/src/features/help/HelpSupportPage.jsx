import { useCallback, useEffect, useState } from 'react'
import { LifeBuoy } from 'lucide-react'
import { createTicket, getMyTicketsPage } from '../../services/helpService'
import { readError } from '../../utils/apiError'
import StatusPill from '../../components/common/StatusPill'
import EmptyState from '../../components/common/EmptyState'
import Pagination from '../../components/common/Pagination'
import { Notice, PageHeader } from '../admin/shared'
import { formatDate } from '../admin/format'

const SUBJECT_MAX = 200

function HelpSupportPage() {
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [sent, setSent] = useState('')
  const [busy, setBusy] = useState(false)
  const [page, setPage] = useState(1)
  const [list, setList] = useState(null)
  const [listError, setListError] = useState('')

  const load = useCallback(
    (target) => getMyTicketsPage(target).then((res) => { setList(res); setListError('') }).catch(() => setListError('Could not load your tickets.')),
    [],
  )
  useEffect(() => { load(page) }, [load, page])

  async function submit(event) {
    event.preventDefault()
    const found = {}
    if (!subject.trim()) found.subject = 'Give the ticket a subject.'
    if (!description.trim()) found.description = 'Describe the problem.'
    setErrors(found)
    setFormError('')
    setSent('')
    if (Object.keys(found).length) return
    setBusy(true)
    try {
      await createTicket(subject.trim(), description.trim())
      setSubject('')
      setDescription('')
      setSent('Your ticket was sent. The Ordinis team will answer here.')
      if (page === 1) await load(1)
      else setPage(1)
    } catch (err) {
      setFormError(readError(err, 'The ticket could not be sent.').message)
    } finally {
      setBusy(false)
    }
  }

  const field = 'w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm text-[#14142B] outline-none focus:border-[#6C31D6]'
  return (
    <div className="space-y-8 max-w-3xl">
      <PageHeader title="Help & Support" subtitle="Something wrong? Send the Ordinis team a ticket and follow it here." />

      <form onSubmit={submit} noValidate className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5 space-y-4" data-testid="ticket-form">
        <div>
          <label htmlFor="ticket-subject" className="block text-sm font-medium text-[#14142B] mb-1">Subject</label>
          <input id="ticket-subject" data-testid="ticket-subject" maxLength={SUBJECT_MAX} value={subject} onChange={(e) => setSubject(e.target.value)} className={field} />
          {errors.subject && <p role="alert" className="text-xs text-[#DC2626] mt-1">{errors.subject}</p>}
        </div>
        <div>
          <label htmlFor="ticket-description" className="block text-sm font-medium text-[#14142B] mb-1">What happened?</label>
          <textarea id="ticket-description" data-testid="ticket-description" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} className={field} />
          {errors.description && <p role="alert" className="text-xs text-[#DC2626] mt-1">{errors.description}</p>}
        </div>
        {formError && <Notice>{formError}</Notice>}
        {sent && <p role="status" data-testid="ticket-sent" className="rounded-lg bg-[#F0FDF4] text-sm text-[#15803D] px-3 py-2">{sent}</p>}
        <button type="submit" data-testid="ticket-submit" disabled={busy} className="bg-[#6C31D6] hover:bg-[#5A28B0] disabled:opacity-60 text-white rounded-lg px-4 py-2 text-sm font-medium transition">
          Send ticket
        </button>
      </form>

      <section>
        <h2 className="text-base font-semibold text-[#14142B] mb-3">Your tickets</h2>
        {listError && <Notice>{listError}</Notice>}
        {list && list.items.length === 0 && <EmptyState icon={LifeBuoy} title="No tickets yet" description="When you send one, it appears here with its status." />}
        {list && list.items.length > 0 && (
          <div className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm divide-y divide-[#EEEEF2]" data-testid="ticket-list">
            {list.items.map((t) => (
              <div key={t.id} data-testid="ticket-item" className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <p data-testid="ticket-item-subject" className="text-sm font-medium text-[#14142B]">{t.subject}</p>
                  <span data-testid="ticket-item-status"><StatusPill status={t.status === 'open' ? 'warning' : 'success'} label={t.status === 'open' ? 'Open' : 'Resolved'} /></span>
                </div>
                {t.description && <p className="text-xs text-[#71717A] mt-1 whitespace-pre-line">{t.description}</p>}
                <p className="text-xs text-[#71717A] mt-1">Sent {formatDate(t.created_at)}{t.resolved_at ? ` · Resolved ${formatDate(t.resolved_at)}` : ''}</p>
                {t.resolution_note && (
                  <p data-testid="ticket-item-note" className="text-sm text-[#15803D] bg-[#F0FDF4] rounded-lg px-3 py-2 mt-2">Answer from Ordinis: {t.resolution_note}</p>
                )}
              </div>
            ))}
          </div>
        )}
        {list && <Pagination page={list.page} totalPages={list.totalPages} count={list.count} pageSize={list.pageSize} onChange={setPage} />}
      </section>
    </div>
  )
}

export default HelpSupportPage
