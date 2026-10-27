import { Link } from 'react-router-dom'
import StatusPill from '../../components/common/StatusPill'
import { formatDate } from '../subscribe/subscribeFormat'
import { timelineView } from './timelineFormat'

const BAR = { success: 'bg-[#6C31D6]', warning: 'bg-[#F59E0B]', failed: 'bg-[#DC2626]' }

// The top of the Billing page: how long the plan has left, and the Renew button.
function TimelineCard({ timeline, planName, canPay, pending }) {
  const view = timelineView(timeline)
  return (
    <div data-testid="timeline-card" data-status={view.status.key} className="bg-white rounded-xl shadow-sm border border-[#EEEEF2] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-[#71717A]">Your plan</p>
          <p data-testid="timeline-plan" className="text-xl font-bold text-[#14142B]">{planName}</p>
        </div>
        <span data-testid="timeline-status"><StatusPill status={view.status.tone} label={view.status.label} /></span>
      </div>

      <div className="mt-4 flex items-end gap-3">
        <p data-testid="timeline-days" className="text-5xl font-bold text-[#14142B] leading-none">{view.big}</p>
        <p data-testid="timeline-caption" className="text-sm text-[#71717A] pb-1">{view.caption}</p>
      </div>

      <div
        className="mt-4 h-2.5 rounded-full bg-[#EEEEF2] overflow-hidden"
        role="progressbar" aria-label="Time used" aria-valuenow={view.percent} aria-valuemin={0} aria-valuemax={100}
      >
        <div data-testid="timeline-bar" className={`h-full rounded-full transition-all duration-300 ${BAR[view.status.tone]}`} style={{ width: `${view.percent}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-[#71717A]">
        <span>Started <span data-testid="timeline-start" className="text-[#14142B] font-medium">{formatDate(timeline.period_start)}</span></span>
        <span>Ends <span data-testid="timeline-end" className="text-[#14142B] font-medium">{formatDate(timeline.period_end)}</span></span>
      </div>

      {canPay && !pending && (
        <div className="mt-4">
          <Link to="/settings/billing/renew" data-testid="renew-btn" className="inline-block bg-[#6C31D6] hover:bg-[#5A28B0] text-white rounded-lg px-5 py-2 text-sm font-medium transition">
            Renew
          </Link>
        </div>
      )}
    </div>
  )
}

export default TimelineCard
