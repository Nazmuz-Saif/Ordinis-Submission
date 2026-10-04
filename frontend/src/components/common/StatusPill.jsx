import { AlertTriangle, CheckCircle2, Info, MinusCircle, XCircle } from 'lucide-react'

// Status is always shown as icon + text, never by color alone.
const VARIANTS = {
  success: { label: 'Success', icon: CheckCircle2, className: 'bg-[#16A34A]/10 text-[#15803D]' },
  warning: { label: 'Warning', icon: AlertTriangle, className: 'bg-[#F59E0B]/10 text-[#B45309]' },
  failed: { label: 'Failed', icon: XCircle, className: 'bg-[#DC2626]/10 text-[#B91C1C]' },
  info: { label: 'Info', icon: Info, className: 'bg-[#3B82F6]/10 text-[#1D4ED8]' },
  neutral: { label: 'Neutral', icon: MinusCircle, className: 'bg-[#71717A]/10 text-[#52525B]' },
}

// Names used elsewhere in the product map onto the five variants.
const ALIASES = { approved: 'success', pending: 'warning', rejected: 'failed', danger: 'failed' }

function StatusPill({ status = 'neutral', label }) {
  const key = ALIASES[status] || status
  const variant = VARIANTS[key] || VARIANTS.neutral
  const Icon = variant.icon
  return (
    <span
      data-testid={`status-pill-${key}`}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors duration-150 ${variant.className}`}
    >
      <Icon size={12} aria-hidden="true" />
      {label || variant.label}
    </span>
  )
}

export default StatusPill
