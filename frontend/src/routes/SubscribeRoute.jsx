import { Navigate } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'
import { isPendingPayment } from '../utils/subscription'

// The /subscribe pages are only for a company that is waiting for its first payment. Everyone else goes to the
// dashboard, which is also where an approved company lands by itself.
function SubscribeRoute({ children }) {
  const { me, loading } = useAuth()
  if (loading || !me) return null
  if (me.is_platform_admin) return <Navigate to="/admin/companies" replace />
  if (!isPendingPayment(me)) return <Navigate to="/dashboard" replace />
  return children
}

export default SubscribeRoute
