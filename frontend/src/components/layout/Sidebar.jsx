import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { ChevronDown, Layers } from 'lucide-react'
import { useAuth } from '../../store/AuthContext'
import PlanBadge from '../common/PlanBadge'
import { isPathActive, visibleNav } from './navigation'

const itemBase = 'flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors duration-150'

function Soon() {
  return <span className="ml-auto text-[10px] rounded-full bg-[#EEEEF2] text-[#71717A] px-1.5 py-0.5">Soon</span>
}

function NavItem({ item, pathname, onNavigate, nested = false }) {
  const Icon = item.icon
  const padding = nested ? 'pl-9' : ''
  if (item.soon) {
    return (
      <div aria-disabled="true" className={`${itemBase} ${padding} text-[#71717A]/60 cursor-default`}>
        {Icon && <Icon size={17} />}
        {item.label}
        <Soon />
      </div>
    )
  }
  const active = isPathActive(pathname, item.path)
  return (
    <Link
      to={item.path}
      onClick={onNavigate}
      data-testid={`sidebar-link-${item.label}`}
      aria-current={active ? 'page' : undefined}
      className={`${itemBase} ${padding} ${
        active ? 'bg-[#EDE9FE] text-[#6C31D6] font-medium' : 'text-[#14142B]/80 hover:bg-[#FAFAFA] hover:text-[#14142B]'
      }`}
    >
      {Icon && <Icon size={17} />}
      {item.label}
    </Link>
  )
}

function NavGroup({ group, pathname, isOpen, onToggle, onNavigate }) {
  const Icon = group.icon
  return (
    <div>
      <button
        onClick={onToggle}
        data-testid={`sidebar-group-${group.key}`}
        aria-expanded={isOpen}
        className={`${itemBase} w-full text-[#14142B]/80 hover:bg-[#FAFAFA] hover:text-[#14142B]`}
      >
        <Icon size={17} />
        {group.label}
        <ChevronDown
          size={15}
          className={`ml-auto transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>
      <div
        className={`grid transition-all duration-200 ${isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
      >
        <div className="overflow-hidden">
          <div data-testid={`sidebar-group-${group.key}-items`} className="space-y-0.5 pt-0.5">
            {group.items.map((item) => (
              <NavItem key={item.path} item={item} pathname={pathname} onNavigate={onNavigate} nested />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function initials(email) {
  return (email || '?').slice(0, 2).toUpperCase()
}

function Sidebar({ open, onClose }) {
  const { me, hasPermission } = useAuth()
  const { pathname } = useLocation()
  // Only groups the user clicked are stored; every other group opens when it holds the active page.
  const [toggled, setToggled] = useState({})
  const nav = visibleNav(hasPermission)

  const isGroupOpen = (group) =>
    group.key in toggled ? toggled[group.key] : group.items.some((i) => isPathActive(pathname, i.path))

  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-[#14142B]/40 md:hidden" onClick={onClose} />}
      <aside
        data-testid="sidebar"
        className={`fixed md:sticky top-0 z-40 h-screen w-64 shrink-0 bg-white border-r border-[#EEEEF2] flex flex-col transition-transform duration-200 ${
          open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="flex items-center gap-2.5 px-5 h-16 border-b border-[#EEEEF2]">
          <div className="w-8 h-8 rounded-lg bg-[#6C31D6] text-white flex items-center justify-center">
            <Layers size={17} />
          </div>
          <span className="text-lg font-bold text-[#14142B]">Ordinis</span>
          <PlanBadge name={me?.plan_name} />
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {nav.map((entry) =>
            entry.type === 'group' ? (
              <NavGroup
                key={entry.key}
                group={entry}
                pathname={pathname}
                isOpen={isGroupOpen(entry)}
                onToggle={() => setToggled((prev) => ({ ...prev, [entry.key]: !isGroupOpen(entry) }))}
                onNavigate={onClose}
              />
            ) : (
              <NavItem key={entry.path} item={entry} pathname={pathname} onNavigate={onClose} />
            ),
          )}
        </nav>

        <div className="border-t border-[#EEEEF2] p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-[#6C31D6] text-white text-sm font-semibold flex items-center justify-center shrink-0">
            {initials(me?.email)}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-[#14142B] truncate">{me?.email}</p>
            <p className="text-xs text-[#71717A] truncate">{me?.designation_title || ''}</p>
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar
