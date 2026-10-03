import { useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import Navbar from '../components/layout/Navbar'

function DashboardLayout({ children }) {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="flex">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div
        className="flex-1 min-w-0 min-h-screen"
        style={{
          background: 'linear-gradient(135deg, #F1EEFB 0%, #FAFAFA 40%, #FAFAFA 100%)',
        }}
      >
        <Navbar onMenuClick={() => setMenuOpen(true)} />
        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  )
}

export default DashboardLayout
