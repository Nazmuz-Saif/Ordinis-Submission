import { Link } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'

// Replaces every page except Billing and My Profile while the company is restricted.
function RestrictedNotice() {
  const { me, hasPermission } = useAuth()
  const waiting = me?.subscription?.status === 'pending_payment'
  return (
    <div data-testid="restricted-page-message" className="max-w-lg mx-auto mt-16 text-center bg-white border border-[#EEEEF2] rounded-xl p-8">
      <div className="w-12 h-12 rounded-xl bg-[#EDE9FE] text-[#6C31D6] flex items-center justify-center mx-auto mb-4">
        <Lock size={22} />
      </div>
      <h2 className="text-lg font-bold text-[#14142B] mb-2">
        {waiting ? 'Waiting for payment approval' : 'Your subscription has ended'}
      </h2>
      <p className="text-sm text-[#71717A] mb-5">
        {waiting
          ? 'This page opens as soon as the platform team approves your first payment.'
          : 'This page is closed until the plan is renewed. Your data is safe and nothing was deleted.'}
      </p>
      {hasPermission('view_billing') ? (
        <Link to="/settings/billing" data-testid="restricted-billing-link" className="inline-block px-4 py-2 rounded-lg bg-[#6C31D6] text-white text-sm font-medium">
          Go to Billing
        </Link>
      ) : (
        <p className="text-sm text-[#14142B]" data-testid="restricted-ask-owner">Ask your company owner to renew the plan.</p>
      )}
    </div>
  )
}

export default RestrictedNotice
