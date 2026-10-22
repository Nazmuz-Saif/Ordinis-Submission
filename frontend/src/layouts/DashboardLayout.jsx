import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'
import Sidebar from '../components/layout/Sidebar'
import Navbar from '../components/layout/Navbar'
import SubscriptionBanner from '../components/layout/SubscriptionBanner'
import RestrictedNotice from '../components/layout/RestrictedNotice'
import { isRestricted, pathOpenWhenRestricted } from '../utils/subscription'

function DashboardLayout({ children }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { me } = useAuth()
  const { pathname } = useLocation()

  // A temporary password must be replaced first: My Profile is the only page that opens until then.
  if (me?.must_change_password && pathname !== '/profile') {
    return <Navigate to="/profile" replace />
  }

  // A restricted company (waiting for its first payment, or past its end date and grace) keeps only Billing and My Profile.
  const blocked = isRestricted(me) && !pathOpenWhenRestricted(pathname)

  return (
    <div className="flex">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div
        className="flex-1 min-w-0 min-h-screen"
        style={{
          background: 'linear-gradient(135deg, #F1EEFB 0%, #FAFAFA 40%, #FAFAFA 100%)',
        }}
      >
        <Navbar onMenuClick={() => setMenuOpen(true)} />
        <SubscriptionBanner />
        <main className="p-4 md:p-6">{blocked ? <RestrictedNotice /> : children}</main>
      </div>
    </div>
  )
}

export default DashboardLayout
