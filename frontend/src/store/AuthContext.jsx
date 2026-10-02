import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getMe, isAuthenticated } from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)

  // Reload the logged-in user's identity + permissions from the server.
  // Called on app start, and again right after login / registration so the
  // UI never shows a stale (empty) permission list.
  const refreshMe = useCallback(async () => {
    if (!isAuthenticated()) {
      setMe(null)
      return null
    }
    try {
      const data = await getMe()
      setMe(data)
      return data
    } catch {
      setMe(null)
      return null
    }
  }, [])

  const clearMe = useCallback(() => setMe(null), [])

  useEffect(() => {
    refreshMe().finally(() => setLoading(false))
  }, [refreshMe])

  const hasPermission = (permission) => {
    return me?.permissions?.includes(permission) ?? false
  }

  return (
    <AuthContext.Provider value={{ me, setMe, loading, hasPermission, refreshMe, clearMe }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
