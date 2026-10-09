import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { getMe, isAuthenticated } from '../services/authService'

const AuthContext = createContext(null)

// Reads the logged-in user from the server. Returns null when logged out or on any error.
async function fetchMe() {
  if (!isAuthenticated()) return null
  try {
    return await getMe()
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)

  // Reload the logged-in user's identity + permissions from the server.
  // Called on app start, and again right after login / registration so the
  // UI never shows a stale (empty) permission list.
  const refreshMe = useCallback(async () => {
    const data = await fetchMe()
    setMe(data)
    return data
  }, [])

  const clearMe = useCallback(() => setMe(null), [])

  useEffect(() => {
    fetchMe()
      .then(setMe)
      .finally(() => setLoading(false))
  }, [])

  const hasPermission = (permission) => {
    return me?.permissions?.includes(permission) ?? false
  }

  return (
    <AuthContext.Provider value={{ me, setMe, loading, hasPermission, refreshMe, clearMe }}>
      {children}
    </AuthContext.Provider>
  )
}

// The hook lives next to its Provider on purpose (they share one context).
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
