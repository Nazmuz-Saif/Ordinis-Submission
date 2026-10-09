import {
  Building2, CalendarCheck, CheckSquare, GitBranch, LayoutDashboard, Wallet,
} from 'lucide-react'

// Single source of truth for the sidebar and the page title.
// - permission: item is hidden unless the user has this Permission codename
// - soon:       the module is not built yet; shown muted, not clickable
export const NAV = [
  { type: 'link', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  {
    type: 'group', key: 'organization', label: 'Organization', icon: Building2,
    items: [
      { label: 'Departments', path: '/organization' },
      { label: 'Designations', path: '/organization/designations' },
      { label: 'Employees', path: '/organization/employees' },
      { label: 'Roles', path: '/roles', permission: 'manage_roles' },
    ],
  },
  {
    type: 'group', key: 'workflow', label: 'Workflow', icon: GitBranch,
    items: [
      { label: 'Approvals', path: '/approvals/pending' },
      { label: 'Delegation', path: '/approvals/delegations' },
      { label: 'Approval Chains', path: '/approvals/chains', permission: 'manage_approval_chains' },
    ],
  },
  {
    type: 'group', key: 'tasks', label: 'Tasks', icon: CheckSquare,
    items: [
      { label: 'Projects', path: '/tasks/projects', soon: true },
      { label: 'My Tasks', path: '/tasks' },
    ],
  },
  {
    type: 'group', key: 'attendance', label: 'Attendance', icon: CalendarCheck,
    items: [
      { label: 'Check In', path: '/attendance' },
      { label: 'Leave', path: '/attendance/leave', soon: true },
    ],
  },
  {
    type: 'group', key: 'finance', label: 'Finance', icon: Wallet,
    items: [
      { label: 'Salary Structures', path: '/payroll/salary-structures', permission: 'manage_finance' },
      { label: 'Payroll', path: '/payroll', soon: true },
      { label: 'Expenses', path: '/payroll/expenses', soon: true },
    ],
  },
]

// Items the user is allowed to see. Groups with nothing visible disappear.
export function visibleNav(hasPermission) {
  const allowed = (item) => !item.permission || hasPermission(item.permission)
  return NAV.map((entry) =>
    entry.type === 'group' ? { ...entry, items: entry.items.filter(allowed) } : entry,
  ).filter((entry) => entry.type !== 'group' || entry.items.length > 0)
}

export function isPathActive(pathname, path) {
  if (pathname === path) return true
  // /organization is the Departments page; do not let it match every /organization/... route
  return path !== '/organization' && pathname.startsWith(`${path}/`)
}

export function pageTitle(pathname) {
  const all = NAV.flatMap((e) => (e.type === 'group' ? e.items : [e]))
  const match = all
    .filter((item) => isPathActive(pathname, item.path))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return match ? match.label : 'Ordinis'
}
