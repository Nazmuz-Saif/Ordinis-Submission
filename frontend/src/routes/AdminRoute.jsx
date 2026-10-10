import { useAuth } from '../store/AuthContext'
import EmptyState from '../components/common/EmptyState'

// Platform Admin pages. Anyone else (CEO, employee) sees a plain "not allowed" page.
// The server refuses them too: this only avoids a screen full of errors.
function AdminRoute({ children }) {
  const { me, loading } = useAuth()
  if (loading) return null
  if (!me?.is_platform_admin) {
    return (
      <div data-testid="admin-denied">
        <EmptyState title="Platform Admin access only" description="This area is for the Ordinis platform team." />
      </div>
    )
  }
  return children
}

export default AdminRoute
