import { ArrowDownRight, ArrowUpRight } from 'lucide-react'

const TONES = {
  positive: 'bg-[#16A34A]/10 text-[#15803D]',
  negative: 'bg-[#DC2626]/10 text-[#B91C1C]',
  neutral: 'bg-[#71717A]/10 text-[#52525B]',
}

function MetricCard({ label, value, delta, deltaTone = 'neutral', icon: Icon, loading = false }) {
  if (loading) {
    return (
      <div data-testid="metric-card-loading" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
        <div className="skeleton h-3 w-24 rounded" />
        <div className="skeleton h-8 w-20 rounded mt-3" />
        <div className="skeleton h-5 w-28 rounded-full mt-3" />
      </div>
    )
  }

  return (
    <div
      data-testid="metric-card"
      className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5 hover:shadow-md transition-shadow duration-200"
    >
      <div className="flex items-center justify-between">
        <p className="text-sm text-[#71717A]">{label}</p>
        {Icon && <Icon size={18} className="text-[#6C31D6]" aria-hidden="true" />}
      </div>
      <p data-testid="metric-value" className="text-3xl font-bold text-[#14142B] mt-2">{value}</p>
      {delta && (
        <span
          data-testid="metric-delta"
          className={`inline-flex items-center gap-0.5 mt-3 rounded-full px-2 py-0.5 text-xs font-medium ${TONES[deltaTone] || TONES.neutral}`}
        >
          {deltaTone === 'positive' && <ArrowUpRight size={12} aria-hidden="true" />}
          {deltaTone === 'negative' && <ArrowDownRight size={12} aria-hidden="true" />}
          {delta}
        </span>
      )}
    </div>
  )
}

export default MetricCard
