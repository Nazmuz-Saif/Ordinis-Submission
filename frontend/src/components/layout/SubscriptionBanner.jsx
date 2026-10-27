import { Link } from 'react-router-dom'
import { AlertTriangle, Clock } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { bannerFor } from '../../utils/subscription'

const TONES = {
  info: 'bg-blue-50 border-blue-200 text-blue-800',
  warn: 'bg-amber-50 border-amber-200 text-amber-800',
  danger: 'bg-red-50 border-red-200 text-red-700',
}

// Shown at the top of every page of a company whose plan is ending, in grace, expired or waiting for payment.
function SubscriptionBanner() {
  const { me, hasPermission } = useAuth()
  if (me?.is_platform_admin) return null
  const banner = bannerFor(me?.subscription)
  if (!banner) return null
  const Icon = banner.tone === 'info' ? Clock : AlertTriangle
  return (
    <div
      data-testid="subscription-banner"
      data-state={me.subscription.status}
      className={`print:hidden mx-4 md:mx-6 mt-4 p-3 border rounded-lg text-sm flex items-center gap-2 ${TONES[banner.tone]}`}
    >
      <Icon size={16} className="shrink-0" aria-hidden="true" />
      <span>{banner.text}</span>
      {hasPermission('view_billing') && (
        <Link to="/settings/billing" className="ml-auto font-medium underline whitespace-nowrap" data-testid="subscription-banner-link">
          Open Billing
        </Link>
      )}
    </div>
  )
}

export default SubscriptionBanner
