import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../../services/authService'
import { useAuth } from '../../store/AuthContext'

function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { refreshMe } = useAuth()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      await refreshMe()
      navigate('/organization')
    } catch {
      setError('Invalid email or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center px-4">
      <div className="bg-white/70 backdrop-blur-xl border border-white/30 shadow-lg rounded-xl p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-[#14142B] mb-1">Ordinis</h1>
        <p className="text-sm text-[#71717A] mb-6">Build Your Organization. Define Your Workflow.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-[#14142B] mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] transition"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-[#14142B] mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-[#EEEEF2] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#6C31D6] transition"
              required
            />
          </div>

          {error && <p className="text-sm text-[#DC2626]">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#6C31D6] hover:bg-[#A78BFA] text-white rounded-lg py-2 text-sm font-medium transition"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="text-sm text-[#71717A] mt-6 text-center">
          New company?{' '}
          <Link to="/register" className="text-[#6C31D6] hover:underline font-medium">
            Register here
          </Link>
        </p>
      </div>
    </div>
  )
}

export default LoginPage