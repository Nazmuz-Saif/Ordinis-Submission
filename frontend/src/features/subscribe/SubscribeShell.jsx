import { useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { logout } from '../../services/authService'
import { useAuth } from '../../store/AuthContext'

const STEPS = [
  { key: 'plan', label: 'Choose a plan' },
  { key: 'pay', label: 'Pay' },
  { key: 'waiting', label: 'Approval' },
]

// The plain page frame of the onboarding steps: no company menu, because the company cannot work yet.
function SubscribeShell({ step, title, subtitle, children }) {
  const { me, clearMe } = useAuth()
  const navigate = useNavigate()
  const current = STEPS.findIndex((s) => s.key === step)

  function handleLogout() {
    logout()
    clearMe()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA]" style={{ background: 'linear-gradient(135deg, #F1EEFB 0%, #FAFAFA 45%, #FAFAFA 100%)' }}>
      <header className="h-16 bg-white/70 backdrop-blur-xl border-b border-white/30 flex items-center justify-between px-4 md:px-8">
        <p className="text-lg font-bold text-[#14142B]">Ordinis</p>
        <div className="flex items-center gap-4 text-sm">
          <span data-testid="subscribe-user" className="text-[#71717A] hidden sm:inline">{me?.company_name} · {me?.email}</span>
          <button data-testid="logout-button" onClick={handleLogout} className="text-[#6C31D6] font-medium hover:underline">Log out</button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <ol data-testid="subscribe-steps" className="flex items-center gap-2 mb-8 text-sm">
          {STEPS.map((s, i) => {
            const done = i < current
            const active = i === current
            return (
              <li key={s.key} data-testid={`step-${s.key}`} data-active={active} className="flex items-center gap-2">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold ${done || active ? 'bg-[#6C31D6] text-white' : 'bg-[#EEEEF2] text-[#71717A]'}`}>
                  {done ? <Check size={14} aria-hidden="true" /> : i + 1}
                </span>
                <span className={active ? 'font-semibold text-[#14142B]' : 'text-[#71717A]'}>{s.label}</span>
                {i < STEPS.length - 1 && <span className="w-8 h-px bg-[#EEEEF2]" aria-hidden="true" />}
              </li>
            )
          })}
        </ol>

        <h1 className="text-2xl font-bold text-[#14142B]">{title}</h1>
        {subtitle && <p className="text-sm text-[#71717A] mt-1 mb-6 max-w-2xl">{subtitle}</p>}
        {children}
      </main>
    </div>
  )
}

export default SubscribeShell
