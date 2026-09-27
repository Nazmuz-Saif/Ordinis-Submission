import { useAuth } from '../../store/AuthContext'
import { logout } from '../../services/authService'
import { useNavigate } from 'react-router-dom'

function Navbar() {
  const { me } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-16 bg-white/70 backdrop-blur-xl border-b border-white/30 flex items-center justify-between px-6">
      <div>
        <p className="text-sm font-medium text-[#14142B]">{me?.company_name}</p>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm text-[#14142B]">{me?.email}</p>
          <p className="text-xs text-[#71717A]">{me?.designation_title}</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-sm text-[#DC2626] hover:underline"
        >
          Logout
        </button>
      </div>
    </header>
  )
}

export default Navbar