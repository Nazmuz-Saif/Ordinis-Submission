import { NavLink } from 'react-router-dom'

const menuItems = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Departments', path: '/organization' },
  { label: 'Designations', path: '/organization/designations' },
  { label: 'Employees', path: '/organization/employees' },
  { label: 'Tasks', path: '/tasks' },
  { label: 'Attendance', path: '/attendance' },
  { label: 'Notifications', path: '/notifications' },
  { label: 'Roles', path: '/roles' },
  { label: 'Payroll', path: '/payroll' },
  { label: 'Approvals', path: '/approvals' },
]

function Sidebar() {
  const visibleMenuItems = menuItems

  return (
    <aside className="w-60 min-h-screen bg-[#14142B] text-white flex flex-col">
      <div className="px-6 py-5 text-xl font-bold border-b border-white/10">
        Ordinis
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {visibleMenuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end
            className={({ isActive }) =>
              `block px-3 py-2 rounded-lg text-sm transition-colors duration-150 ${isActive
                ? 'bg-[#6C31D6] text-white'
                : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar