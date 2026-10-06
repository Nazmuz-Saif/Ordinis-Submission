import { Navigate } from 'react-router-dom'
import { useAuth } from '../store/AuthContext'
import { isAuthenticated } from '../services/authService'

function FinanceRoute({ children }) {
    const { hasPermission } = useAuth()

    if (!isAuthenticated()) {
        return <Navigate to="/login" replace />
    }

    if (!hasPermission('finance')) {
        return <Navigate to="/organization" replace />
    }

    return children
}

export default FinanceRoute