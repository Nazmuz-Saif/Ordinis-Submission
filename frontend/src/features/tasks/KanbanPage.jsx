import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, CalendarDays, Flag } from 'lucide-react'
import { getBoard, moveTask } from '../../services/tasksService'
import EmptyState from '../../components/common/EmptyState'
import TaskProgressPanel from './TaskProgressPanel'

const PRIORITY = {
  high: 'bg-[#DC2626]/10 text-[#B91C1C]',
  medium: 'bg-[#F59E0B]/10 text-[#B45309]',
  low: 'bg-[#71717A]/10 text-[#52525B]',
}

// Button text for moving a card: depends on where it is and where it goes.
const MOVE_LABEL = {
  'todo>in_progress': 'Start',
  'in_progress>review': 'Submit for review',
  'review>done': 'Approve',
  'review>todo': 'Reject',
}

const columnOf = (board, cardId) => board.columns.find((c) => c.cards.some((card) => card.id === cardId))
const initials = (email) => (email || '?').split('@')[0].slice(0, 2).toUpperCase()
const errorMessage = (err, fallback) => err.response?.data?.error?.message || fallback

function Card({ card, columnKey, dragging, onDragStart, onDragEnd, onMove, onOpen }) {
  return (
    <div
      data-testid="kanban-card" draggable onDragStart={() => onDragStart(card.id)} onDragEnd={onDragEnd}
      className={`bg-white rounded-xl border border-[#EEEEF2] p-3 shadow-sm space-y-2 cursor-grab transition-shadow duration-200 hover:shadow-md ${dragging ? 'opacity-50' : ''}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${PRIORITY[card.priority] || PRIORITY.medium}`}>
          {card.priority}
        </span>
        <div className="flex items-center gap-1.5">
          {card.rejected && <span data-testid="card-rejected" className="text-xs font-medium text-[#B91C1C]">Rejected</span>}
          {card.blocked && (
            <span data-testid="card-blocked" className="flex items-center gap-0.5 text-xs font-medium text-[#B45309]"><Flag size={12} /> Blocked</span>
          )}
        </div>
      </div>

      <button type="button" data-testid="card-title" onClick={() => onOpen(card)} className="text-left font-semibold text-[#14142B] text-sm hover:text-[#6C31D6]">
        {card.title}
      </button>

      <div>
        <div className="h-1.5 rounded-full bg-[#EDE9FE]" role="progressbar" aria-valuenow={card.progress_percent} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-1.5 rounded-full bg-[#6C31D6]" style={{ width: `${card.progress_percent}%` }} />
        </div>
        <p data-testid="card-progress" className="text-xs text-[#71717A] mt-1">{card.progress_percent}%</p>
      </div>

      <div className="flex items-center justify-between text-xs text-[#71717A]">
        <span className="flex items-center gap-1.5 min-w-0">
          <span className="h-5 w-5 shrink-0 rounded-full bg-[#6C31D6] text-white text-[10px] font-semibold flex items-center justify-center">{initials(card.assigned_to_email)}</span>
          <span className="truncate" title={card.assigned_to_email}>{card.assigned_to_email}</span>
        </span>
        {card.deadline && (
          <span data-testid="card-deadline" className={`flex items-center gap-1 whitespace-nowrap ${card.overdue ? 'text-[#B91C1C] font-medium' : ''}`}>
            {card.overdue ? <AlertTriangle size={12} /> : <CalendarDays size={12} />} {card.deadline}
          </span>
        )}
      </div>

      {card.allowed_moves.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {card.allowed_moves.map((target) => (
            <button
              key={target} type="button" data-testid={`card-move-${target}`} onClick={() => onMove(card.id, target)}
              className="text-xs font-medium rounded-lg px-2.5 py-1 border border-[#6C31D6] text-[#6C31D6] hover:bg-[#EDE9FE] transition-colors duration-150"
            >
              {MOVE_LABEL[`${columnKey}>${target}`] || target}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function KanbanPage() {
  const [board, setBoard] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [dragId, setDragId] = useState(null)
  const [openId, setOpenId] = useState(null)

  useEffect(() => {
    let active = true
    getBoard()
      .then((data) => {
        if (active) setBoard(data)
      })
      .catch((err) => {
        if (active) setError(errorMessage(err, 'Failed to load the board.'))
      })
    return () => {
      active = false
    }
  }, [refresh])

  const reload = useCallback(() => setRefresh((n) => n + 1), [])

  async function move(cardId, targetKey) {
    const from = columnOf(board, cardId)
    if (!from || from.key === targetKey) return
    setError('')
    setMessage('')
    try {
      await moveTask(cardId, targetKey)
      setMessage(`Moved to ${board.columns.find((c) => c.key === targetKey).label}.`)
    } catch (err) {
      setError(errorMessage(err, 'Could not move the task.')) // the server explains why
    }
    reload()
  }

  function drop(targetKey) {
    const id = dragId
    setDragId(null)
    if (id) move(id, targetKey)
  }

  const dragged = board && dragId ? board.columns.flatMap((c) => c.cards).find((c) => c.id === dragId) : null
  const openCard = board && openId ? board.columns.flatMap((c) => c.cards).find((c) => c.id === openId) : null

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[#14142B]">Task board</h1>
        <p className="text-sm text-[#71717A] mt-1">Drag a card to the next column, or use its button. Click a title for the progress timeline.</p>
      </div>

      {message && <div role="status" data-testid="board-message" className="rounded-lg bg-[#16A34A]/10 text-[#15803D] px-4 py-3 text-sm">{message}</div>}
      {error && <div role="alert" data-testid="board-error" className="rounded-lg bg-[#DC2626]/10 text-[#B91C1C] px-4 py-3 text-sm">{error}</div>}

      {!board && !error && <div className="skeleton h-64 w-full rounded-xl" />}

      {board && board.columns.every((c) => c.count === 0) && (
        <EmptyState title="No tasks yet" description="Tasks assigned to you, or created by you, appear here." />
      )}

      {board && !board.columns.every((c) => c.count === 0) && (
        <div data-testid="kanban-board" className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 items-start">
          {board.columns.map((col) => {
            const canDrop = dragged?.allowed_moves.includes(col.key)
            return (
              <section
                key={col.key} data-testid={`kanban-column-${col.key}`}
                onDragOver={(e) => e.preventDefault()} onDrop={() => drop(col.key)}
                className={`rounded-xl bg-[#FAFAFA] border p-3 space-y-3 min-h-40 transition-colors duration-150 ${canDrop ? 'border-[#6C31D6] bg-[#EDE9FE]/40' : 'border-[#EEEEF2]'}`}
              >
                <header className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-[#14142B]">{col.label}</h2>
                  <span data-testid={`column-count-${col.key}`} className="rounded-full bg-[#EDE9FE] text-[#6C31D6] text-xs font-semibold px-2 py-0.5">{col.count}</span>
                </header>
                {col.cards.length === 0 && <p className="text-xs text-[#71717A] text-center py-4">No tasks</p>}
                {col.cards.map((card) => (
                  <Card
                    key={card.id} card={card} columnKey={col.key} dragging={dragId === card.id}
                    onDragStart={setDragId} onDragEnd={() => setDragId(null)} onMove={move} onOpen={(c) => setOpenId(c.id)}
                  />
                ))}
                {col.has_more && <p className="text-xs text-[#71717A] text-center">Showing the first {col.cards.length} of {col.count}.</p>}
              </section>
            )
          })}
        </div>
      )}

      {openCard && <TaskProgressPanel key={openCard.id} card={openCard} onClose={() => setOpenId(null)} onChanged={reload} />}
    </div>
  )
}

export default KanbanPage
