import { useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, Building2, ChevronDown, LogOut, Menu, Search } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import { logout } from '../../services/authService'
import useClickOutside from '../../hooks/useClickOutside'
import EmptyState from '../common/EmptyState'
import { pageTitle } from './navigation'

function Navbar({ onMenuClick }) {
  const { me, clearMe } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const [bellOpen, setBellOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)
  const bellRef = useRef(null)
  const userRef = useRef(null)
  useClickOutside(bellRef, () => setBellOpen(false), bellOpen)
  useClickOutside(userRef, () => setUserOpen(false), userOpen)

  function handleLogout() {
    logout()
    clearMe()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-20 h-16 bg-white/70 backdrop-blur-xl border-b border-white/30 flex items-center gap-4 px-4 md:px-6">
      <button onClick={onMenuClick} aria-label="Open menu" className="md:hidden p-2 -ml-2 text-[#14142B]">
        <Menu size={20} />
      </button>

      <p data-testid="page-title" className="text-lg font-bold text-[#14142B] whitespace-nowrap">
        {pageTitle(pathname)}
      </p>

      <div className="hidden md:flex flex-1 max-w-md mx-auto items-center gap-2 bg-[#EEEEF2]/70 rounded-full px-4 py-2">
        <Search size={16} className="text-[#71717A]" aria-hidden="true" />
        <input
          type="search"
          placeholder="Search..."
          aria-label="Search"
          data-testid="navbar-search"
          className="bg-transparent outline-none text-sm w-full text-[#14142B] placeholder:text-[#71717A]"
        />
      </div>

      <div className="ml-auto flex items-center gap-2 md:gap-3">
        <div
          data-testid="navbar-company"
          className="hidden sm:flex items-center gap-1.5 text-sm text-[#14142B] bg-white border border-[#EEEEF2] rounded-lg px-3 py-1.5"
        >
          <Building2 size={15} className="text-[#6C31D6]" aria-hidden="true" />
          {me?.is_platform_admin ? 'Ordinis Platform' : me?.company_name}
        </div>

        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setBellOpen((v) => !v)}
            aria-label="Notifications"
            aria-expanded={bellOpen}
            data-testid="notification-bell"
            className="p-2 rounded-lg text-[#14142B] hover:bg-white transition-colors duration-150"
          >
            <Bell size={19} />
          </button>
          {bellOpen && (
            <div
              data-testid="notification-dropdown"
              className="absolute right-0 mt-2 w-80 bg-white rounded-xl border border-[#EEEEF2] shadow-lg p-3"
            >
              <p className="text-sm font-semibold text-[#14142B] px-1 pb-2">Notifications</p>
              <EmptyState title="You're all caught up" description="New notifications will show up here." />
            </div>
          )}
        </div>

        <div className="relative" ref={userRef}>
          <button
            onClick={() => setUserOpen((v) => !v)}
            aria-expanded={userOpen}
            data-testid="user-menu-button"
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-white transition-colors duration-150"
          >
            <span className="w-8 h-8 rounded-full bg-[#6C31D6] text-white text-xs font-semibold flex items-center justify-center">
              {(me?.email || '?').slice(0, 2).toUpperCase()}
            </span>
            <span className="hidden md:block text-sm text-[#14142B] max-w-[10rem] truncate">{me?.email}</span>
            <ChevronDown size={14} className="text-[#71717A]" />
          </button>
          {userOpen && (
            <div
              data-testid="user-menu"
              className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-[#EEEEF2] shadow-lg py-2"
            >
              <div className="px-4 pb-2 border-b border-[#EEEEF2]">
                <p className="text-sm font-medium text-[#14142B] truncate">{me?.email}</p>
                <p className="text-xs text-[#71717A]">{me?.designation_title || ''}</p>
              </div>
              <button
                onClick={handleLogout}
                data-testid="logout-button"
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-[#DC2626] hover:bg-[#FAFAFA]"
              >
                <LogOut size={15} /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Navbar
