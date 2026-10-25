import {
  BarChart3, Building2, CalendarCheck, CalendarClock, CheckSquare, CreditCard, GitBranch, History, Inbox, LayoutDashboard, LifeBuoy, ScrollText, ShieldCheck, Settings, Wallet,
} from 'lucide-react'

// Single source of truth for the sidebar and the page title.
// - permission: item is hidden unless the user has this Permission codename
// - soon:       the module is not built yet; shown muted, not clickable
export const NAV = [
  { type: 'link', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { type: 'link', label: 'Action Inbox', path: '/inbox', icon: Inbox },
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
      { label: 'Board', path: '/tasks/board' },
    ],
  },
  {
    type: 'group', key: 'attendance', label: 'Attendance', icon: CalendarCheck,
    items: [
      { label: 'Check In', path: '/attendance' },
      { label: 'Leave', path: '/attendance/leave' },
      { label: 'Team Attendance', path: '/attendance/team', permission: 'view_team_attendance', orTeam: true },
      { label: 'Leave Types', path: '/attendance/leave-types', permission: 'manage_leave_types' },
    ],
  },
  {
    type: 'group', key: 'finance', label: 'Finance', icon: Wallet,
    items: [
      { label: 'Salary Structures', path: '/payroll/salary-structures', permission: 'manage_finance' },
      { label: 'Payslips', path: '/payroll/payslips', permission: 'manage_finance' },
      { label: 'My Payslips', path: '/payroll/my-payslips' },
      { label: 'Payroll', path: '/payroll', soon: true },
      { label: 'Expenses', path: '/payroll/expenses', soon: true },
    ],
  },
  { type: 'link', label: 'Analytics', path: '/analytics', icon: BarChart3, permission: 'view_analytics' },
  { type: 'link', label: 'Audit Logs', path: '/audit-logs', icon: ScrollText, permission: 'view_audit_log' },
  {
    type: 'group', key: 'settings', label: 'Settings', icon: Settings,
    items: [
      { label: 'Support Access', path: '/settings/support-access', permission: 'approve_support_access' },
      { label: 'Billing', path: '/settings/billing', permission: 'view_billing', openWhenRestricted: true },
    ],
  },
]

// Items the user is allowed to see. Groups with nothing visible disappear.
export function visibleNav(hasPermission, isPlatformAdmin = false, hasTeam = false, restricted = false) {
  if (isPlatformAdmin) return ADMIN_NAV // a Platform Admin has no company, so no company menu
  // orTeam: the Permission OR having people below you (Team Attendance)
  // restricted: a company waiting for payment or past its end keeps only the items marked openWhenRestricted
  const allowed = (item) =>
    (!restricted || item.openWhenRestricted) &&
    (!item.permission || hasPermission(item.permission) || Boolean(item.orTeam && hasTeam))
  return NAV.map((entry) =>
    entry.type === 'group' ? { ...entry, items: entry.items.filter(allowed) } : entry,
  ).filter((entry) => (entry.type === 'group' ? entry.items.length > 0 : allowed(entry)))   // links obey permission too
}

// The menu of a Platform Admin. A normal user never gets these items, not even hidden.
export const ADMIN_NAV = [
  { type: 'link', label: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
  { type: 'link', label: 'Companies', path: '/admin/companies', icon: Building2 },
  { type: 'link', label: 'Payments', path: '/admin/payments', icon: CreditCard, badge: 'pendingPayments' },
  { type: 'link', label: 'Subscriptions', path: '/admin/subscriptions', icon: CalendarClock },
  { type: 'link', label: 'Support Tickets', path: '/admin/tickets', icon: LifeBuoy },
  { type: 'link', label: 'Access Requests', path: '/admin/access-requests', icon: ShieldCheck },
  { type: 'link', label: 'Activity', path: '/admin/activity', icon: History },
]

const EXACT_ONLY = new Set(['/organization', '/tasks', '/payroll', '/attendance'])

export function isPathActive(pathname, path) {
  if (pathname === path) return true
  // /organization (Departments) and /tasks (My Tasks) have sub-pages with their own menu item: match exactly
  return !EXACT_ONLY.has(path) && pathname.startsWith(`${path}/`)
}

export function pageTitle(pathname) {
  const all = [...NAV, ...ADMIN_NAV].flatMap((e) => (e.type === 'group' ? e.items : [e]))
  const match = all
    .filter((item) => isPathActive(pathname, item.path))
    .sort((a, b) => b.path.length - a.path.length)[0]
  if (pathname === '/profile') return 'My Profile'
  return match ? match.label : 'Ordinis'
}
