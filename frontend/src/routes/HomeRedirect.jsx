import { Navigate } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'

// "/dashboard" is the company dashboard. A Platform Admin has no company, so they land on the admin panel.
function HomeRedirect({ children }) {
  const { me, loading } = useAuth()
  if (loading) return null
  if (me?.is_platform_admin) return <Navigate to="/admin/companies" replace />
  return children
}

export default HomeRedirect
