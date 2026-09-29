import { createContext, useContext, useEffect, useState } from 'react'
import { getMe, isAuthenticated } from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isAuthenticated()) {
      getMe()
        .then(setMe)
        .catch(() => setMe(null))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const hasPermission = (permission) => {
    return me?.permissions?.includes(permission) ?? false
  }

  return (
    <AuthContext.Provider value={{ me, setMe, loading, hasPermission }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}