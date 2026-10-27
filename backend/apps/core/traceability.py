"""
Requirement -> story -> status, with the status READ FROM THE CODE.
A requirement is Done when everything it names exists in the code, Partly when some of it does, Not built when none does.
When a teammate's story lands (a model, a route, a class), the status flips by itself on the next
`python manage.py generate_docs`. Only a requirement that cannot be checked from code carries a fixed status and a reason.

Evidence keys:  models  fields ('Model.field')  routes ('/api/v1/...{id}/')  any_routes (one of these)  symbols (class or
function in backend code)  frontend (component names)  route_perms ({(path, method): permission codename})
"""
from core import docgen, doccheck
from core.api_matrix import discover_routes

# id, short text, priority, stories, evidence | fixed (status, reason)
FR = [
    ('FR-1', 'Company self-registration (company, settings, CEO) in one step', 'High', 'ST-101', {'routes': ['/api/v1/auth/register/']}),
    ('FR-2', 'Email and password login with JWT access and refresh tokens', 'High', 'ST-102', {'routes': ['/api/v1/auth/login/', '/api/v1/auth/refresh/']}),
    ('FR-3', 'Login refused for a suspended company, with a clear error', 'High', 'ST-103', {'symbols': ['CustomTokenObtainPairSerializer']}),
    ('FR-4', '"Who am I" endpoint (user, company, designation, permissions)', 'Medium', 'ST-102', {'routes': ['/api/v1/auth/me/']}),
    ('FR-5', 'Departments: create, view, update, delete', 'High', 'ST-104', {'routes': ['/api/v1/organization/departments/', '/api/v1/organization/departments/{id}/']}),
    ('FR-6', 'Designations: create, view, update, delete', 'High', 'ST-105', {'routes': ['/api/v1/organization/designations/', '/api/v1/organization/designations/{id}/']}),
    ('FR-7', 'Employees with department, designation and manager (reports_to)', 'High', 'ST-106', {'routes': ['/api/v1/organization/employees/'], 'fields': ['Employee.department', 'Employee.designation', 'Employee.reports_to']}),
    ('FR-8', 'Arbitrary-depth reporting hierarchy through reports_to', 'High', 'ST-106', {'fields': ['Employee.reports_to'], 'symbols': ['get_all_subordinates']}),
    ('FR-9', 'Full list of subordinates and managers resolved recursively', 'Medium', 'ST-107', {'routes': ['/api/v1/organization/employees/{id}/subordinates/'], 'symbols': ['get_all_subordinates', 'get_all_managers']}),
    ('FR-10', 'Company Roles as named bundles of Permissions', 'High', 'ST-108', {'models': ['Role', 'Permission'], 'routes': ['/api/v1/rbac/roles/', '/api/v1/rbac/permissions/']}),
    ('FR-11', 'Roles assigned to any Employee, independent of Designation', 'High', 'ST-109', {'models': ['EmployeeRole'], 'routes': ['/api/v1/rbac/employee-roles/']}),
    ('FR-12', 'A specific Permission codename is checked before every protected action', 'High', 'ST-110, ST-111', {'symbols': ['PermissionRequiredMixin', 'HasPermission']}),
    ('FR-13', 'Operational data visible only to the employee, the manager chain and company-wide permission holders', 'High', 'ST-107, ST-111, ST-116, ST-144',
        {'routes': ['/api/v1/attendance/attendance/team/', '/api/v1/attendance/attendance/team/people/'], 'symbols': ['team_scope', 'IsHierarchySuperior']}),
    ('FR-14', 'Approval Chain of ordered steps, each tied to a Role', 'Medium', 'ST-112', {'models': ['ApprovalChain', 'ApprovalStep'], 'routes': ['/api/v1/approvals/chains/', '/api/v1/approvals/steps/']}),
    ('FR-15', 'Every approve or reject recorded with actor and comment', 'Medium', 'ST-113', {'models': ['ApprovalAction'], 'routes': ['/api/v1/approvals/instances/{id}/approve/', '/api/v1/approvals/instances/{id}/reject/']}),
    ('FR-16', 'Delegation of approval authority for a date range', 'Medium', 'ST-117', {'models': ['DelegationRule'], 'routes': ['/api/v1/approvals/delegations/']}),
    ('FR-17', 'Projects and Tasks with status, priority, deadline', 'High', 'ST-116, ST-125', {'models': ['Task', 'Project'], 'routes': ['/api/v1/tasks/tasks/']}),
    ('FR-18', 'Task status changes only along valid transitions', 'High', 'ST-116, ST-125', {'routes': ['/api/v1/tasks/tasks/{id}/submit/', '/api/v1/tasks/tasks/{id}/move/'], 'symbols': ['move_task', 'submit_task']}),
    ('FR-19', 'Daily progress log, comments and attachment links on a Task', 'Medium', 'ST-125', {'models': ['TaskProgressLog', 'TaskComment', 'TaskAttachment'], 'routes': ['/api/v1/tasks/tasks/{id}/progress/']}),
    ('FR-20', 'One check-in and one check-out per day in the company time zone', 'High', 'ST-119', {'routes': ['/api/v1/attendance/attendance/check_in/', '/api/v1/attendance/attendance/check_out/']}),
    ('FR-21', 'Leave application validated against the remaining balance', 'High', 'ST-128', {'models': ['LeaveRequest', 'LeaveType'], 'routes': ['/api/v1/attendance/leave-requests/', '/api/v1/attendance/leave-requests/balance/'], 'symbols': ['apply_leave']}),
    ('FR-22', 'An approver approves or rejects a Pending leave request', 'High', 'ST-129', {'routes': ['/api/v1/approvals/instances/{id}/approve/'], 'symbols': ['on_approval_finished']}),
    ('FR-23', 'Leave Types and a Holiday Calendar per company', 'Medium', 'ST-128', {'models': ['LeaveType', 'HolidayCalendar'], 'routes': ['/api/v1/attendance/leave-types/']}),
    ('FR-24', 'Salary Structure per Employee (base salary and allowances)', 'High', 'ST-118, ST-120', {'models': ['SalaryStructure'], 'routes': ['/api/v1/payroll/salary-structures/']}),
    ('FR-25', 'Payslip per Employee and month, no duplicates', 'High', 'ST-127', {'models': ['Payslip'], 'routes': ['/api/v1/payroll/payslips/'], 'symbols': ['generate_payslip']}),
    ('FR-26', 'Expense claims approved or rejected', 'Medium', '(not in the 5 sprints)', {'models': ['Expense']}),
    ('FR-27', 'Reimbursement recorded against an approved Expense', 'Medium', '(not in the 5 sprints)', {'models': ['Reimbursement']}),
    ('FR-28', 'Salary and payslip data limited to the finance Permission', 'High', 'ST-118, ST-120, ST-127', {'route_perms': {('/api/v1/payroll/salary-structures/', 'get'): 'manage_finance', ('/api/v1/payroll/payslips/', 'post'): 'manage_finance'}}),
    ('FR-29', 'In-app Notification for task assignment and approvals', 'Medium', 'ST-126', {'models': ['Notification'], 'routes': ['/api/v1/notifications/']}),
    ('FR-30', 'Action Inbox combining tasks, approvals and notifications', 'Medium', 'ST-126', {'routes': ['/api/v1/notifications/inbox/']}),
    ('FR-31', 'Append-only Audit Log of every create, update and delete', 'High', 'ST-135', {'models': ['AuditLog']}),
    ('FR-32', 'Company health analytics (attendance rate, task completion)', 'Low', 'ST-134', {'models': ['CompanyHealthSnapshot'], 'routes': ['/api/v1/analytics/overview/']}),
    ('FR-33', 'Employee limit enforced by the subscription plan', 'Medium', 'ST-136', {'models': ['SubscriptionPlan', 'Subscription'], 'symbols': ['can_add_employee']}),
    ('FR-34', 'Platform Admin must send a Support Access Request with a reason', 'Medium', 'ST-123', {'models': ['SupportAccessRequest'], 'routes': ['/api/v1/platform-admin/requests/']}),
    ('FR-35', 'The company approves; access is time-limited and expires by itself', 'Medium', 'ST-123', {'routes': ['/api/v1/platform-admin/company/access-requests/{id}/approve/', '/api/v1/platform-admin/company/access-requests/{id}/revoke/']}),
    ('FR-36', 'Every Break-Glass access recorded where the company can read it', 'Medium', 'ST-123, ST-124', {'models': ['ImpersonationLog'], 'routes': ['/api/v1/platform-admin/company/access-log/']}),
    # --- Sprint 6 (ST-138 to ST-154) ---
    ('FR-37', 'Every Permission has a name, a plain-language description and a module, kept in one place in the code', 'High', 'ST-138',
        {'fields': ['Permission.name', 'Permission.description', 'Permission.module'], 'routes': ['/api/v1/rbac/permissions/'], 'frontend': ['PermissionPicker']}),
    ('FR-38', 'Roles page with Permissions in sections, a detail page that explains each Permission, and editing a Role', 'High', 'ST-139',
        {'routes': ['/api/v1/rbac/roles/{id}/'], 'symbols': ['RoleInUse'], 'frontend': ['RolesPage', 'RoleDetailPage', 'PermissionPicker']}),
    ('FR-39', 'Full name and profile details stored; every user sees and edits their own My Profile', 'High', 'ST-140, ST-141',
        {'fields': ['User.full_name', 'Employee.phone', 'Employee.address', 'Employee.emergency_contact_name'], 'routes': ['/api/v1/auth/profile/'], 'frontend': ['MyProfilePage']}),
    ('FR-40', 'Change password with the current password; a temporary password for a new employee that must be changed at first login', 'High', 'ST-142',
        {'fields': ['User.must_change_password'], 'routes': ['/api/v1/auth/change-password/']}),
    ('FR-41', 'Employee detail page with the full profile and the Permissions the person really has', 'Medium', 'ST-143',
        {'routes': ['/api/v1/organization/employees/{id}/access/'], 'frontend': ['EmployeeDetailPage']}),
    ('FR-42', 'A CEO or a manager picks an employee and sees the month of attendance with check-in and check-out times', 'Medium', 'ST-144',
        {'routes': ['/api/v1/attendance/attendance/team/', '/api/v1/attendance/attendance/team/people/'], 'symbols': ['team_month'], 'frontend': ['TeamAttendancePage']}),
    ('FR-43', 'A subscription has a start and end date, days left, reminders, a grace period and then a restricted mode', 'High', 'ST-145, ST-149',
        {'models': ['Subscription'], 'fields': ['Subscription.current_period_end'], 'symbols': ['restriction_for', 'process_subscriptions', 'is_restricted'], 'routes': ['/api/v1/billing/subscription/']}),
    ('FR-44', 'A company chooses a plan and months, pays outside the system and sends the payment details; it starts only after approval', 'High', 'ST-146, ST-147',
        {'models': ['PaymentSubmission'], 'routes': ['/api/v1/billing/payments/', '/api/v1/billing/quote/', '/api/v1/billing/payment-instructions/'], 'frontend': ['ChoosePlanPage', 'PaymentPage', 'WaitingPage']}),
    ('FR-45', 'The Platform Admin reviews each manual payment and approves it, or rejects it with a note', 'High', 'ST-148',
        {'routes': ['/api/v1/platform-admin/admin/payments/{id}/approve/', '/api/v1/platform-admin/admin/payments/{id}/reject/', '/api/v1/platform-admin/admin/payments/pending-count/'], 'frontend': ['PaymentsPage', 'SubscriptionsPage']}),
    ('FR-46', 'Billing timeline with days left, Renew against a renewal invoice, and a detail page for every invoice', 'Medium', 'ST-149',
        {'models': ['Invoice'], 'routes': ['/api/v1/billing/invoices/{id}/'], 'symbols': ['ensure_renewal_invoice'], 'frontend': ['TimelineCard', 'RenewPage', 'InvoiceDetailPage']}),
    ('FR-47', 'A detail page for each Department (with its head) and each Designation: who is in it and what work is running', 'Medium', 'ST-150',
        {'fields': ['Department.head'], 'routes': ['/api/v1/organization/departments/{id}/overview/', '/api/v1/organization/designations/{id}/overview/'], 'frontend': ['DepartmentDetailPage', 'DesignationDetailPage']}),
    ('FR-48', 'A higher plan is paid for the days left and starts when approved; a lower plan starts at the next renewal', 'Medium', 'ST-151',
        {'fields': ['Subscription.next_plan'], 'routes': ['/api/v1/billing/upgrade-quote/', '/api/v1/billing/downgrade/'], 'symbols': ['upgrade_quote', 'schedule_downgrade', 'apply_scheduled_plan'], 'frontend': ['ChangePlanPage']}),
    ('FR-49', 'The Platform Admin opens a company detail page (owner, plan, size, counts) that never shows employee data', 'Medium', 'ST-152',
        {'routes': ['/api/v1/platform-admin/admin/companies/{id}/'], 'symbols': ['company_detail'], 'frontend': ['CompanyDetailPage']}),
    ('FR-50', 'A Platform Admin dashboard with companies by state, revenue, dues and what needs attention', 'Medium', 'ST-153',
        {'routes': ['/api/v1/platform-admin/admin/summary/'], 'symbols': ['platform_summary'], 'frontend': ['AdminDashboardPage']}),
    ('FR-51', 'Every suspend, activate and ticket resolution carries a written note; a company reads its own tickets and the answer', 'Medium', 'ST-154',
        {'fields': ['SupportTicket.resolution_note'], 'routes': ['/api/v1/platform-admin/company/tickets/'], 'symbols': ['clean_note'], 'frontend': ['HelpSupportPage', 'NoteDialog', 'RequestAccessDialog']}),
]

NFR = [
    ('NFR-1', 'Passwords stored with a one-way hash (PBKDF2)', 'High', 'ST-101, ST-102',
        ('Done', 'Django default hasher. A fast hasher is used only while the tests run (settings/base.py).')),
    ('NFR-2', 'Tenant isolation: another company\'s object is a 404, not a 403', 'High', 'ST-111, ST-131', {'symbols': ['IsCompanyActive'], 'routes': ['/api/v1/tenants/company/']}),
    ('NFR-3', 'Short-lived access token, rotating refresh token, blacklist on logout', 'High', 'ST-102', {'routes': ['/api/v1/auth/refresh/', '/api/v1/auth/logout/']}),
    ('NFR-4', 'Every protected endpoint checks its Permission on the server; secure by default', 'High', 'ST-110, ST-111, ST-131', {'symbols': ['PermissionRequiredMixin', 'HasPermission', 'IsCompanyActive']}),
    ('NFR-5', 'All list endpoints are paginated', 'Medium', 'ST-121', {'symbols': ['OrdinisPagination']}),
    ('NFR-6', 'Standard pages answer within a few seconds under demo load', 'Low', 'ST-121',
        ('Partly', 'No timing was measured. Tests assert the query count does not grow with the number of records on the board, inbox, dashboard and payslip lists.')),
    ('NFR-7', 'One consistent minimalist design across every module', 'Medium', 'ST-114, ST-115', {'frontend': ['StatusPill', 'MetricCard', 'EmptyState', 'ChartCard', 'Sidebar', 'Navbar']}),
    ('NFR-8', 'Specific, actionable error messages', 'Medium', 'ST-111, ST-128', ('Done', 'Business rules return a named code and a readable message (for example the remaining leave days).')),
    ('NFR-9', 'Core actions within a few clicks, little or no training', 'Medium', 'ST-122',
        ('Partly', 'Role dashboards and an Action Inbox exist. No usability test with real users was run.')),
    ('NFR-10', 'Payslip generation is idempotent', 'High', 'ST-127', {'symbols': ['PayslipError', 'generate_payslip']}),
    ('NFR-11', 'Leave balance and Task transitions enforced in the service layer', 'Medium', 'ST-116, ST-128', {'symbols': ['apply_leave', 'check_transition']}),
    ('NFR-12', 'Business logic in service modules, not in views', 'Medium', 'ST-111', ('Done', 'services.py in organization, tasks, attendance, payroll, approvals, notifications, platform_admin, dashboard.')),
    ('NFR-13', 'Hierarchy, roles and approval chains are data, not code', 'High', 'ST-106, ST-108, ST-112', {'models': ['Role', 'ApprovalChain'], 'fields': ['Employee.reports_to']}),
    ('NFR-14', 'Versioned REST API under /api/v1/', 'Low', 'ST-102', {'routes': ['/api/v1/auth/login/']}),
    ('NFR-15', 'Every sensitive action attributable to an actor and a time', 'High', 'ST-123, ST-135', {'models': ['AuditLog', 'PlatformActionLog', 'ImpersonationLog']}),
]

_PATH_ID = '{pk}'


def _code_symbols():
    import ast
    import os
    found = set()
    for root, _dirs, files in os.walk(docgen.APPS_DIR):
        if 'migrations' in root:
            continue
        for name in files:
            if name.endswith('.py'):
                try:
                    tree = ast.parse(open(os.path.join(root, name), encoding='utf-8').read())
                except SyntaxError:
                    continue
                found.update(n.name for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef)))
    return found


class Facts:
    def __init__(self):
        self.models = {m.__name__ for _a, ms in docgen.our_models() for m in ms}
        self.fields = {f'{k}.{f}' for k, fs in doccheck.model_fields().items() for f in fs}
        self.routes_list = discover_routes()
        self.routes = {'/' + r.template.replace(_PATH_ID, '{id}') for r in self.routes_list}
        self.symbols = _code_symbols() | set(doccheck.known_classes())
        self.frontend = doccheck.frontend_names()

    def route(self, path):
        return next((r for r in self.routes_list if '/' + r.template.replace(_PATH_ID, '{id}') == path), None)


def evaluate(evidence, facts):
    """(have, missing) lists of human-readable items."""
    have, missing = [], []

    def add(ok, label):
        (have if ok else missing).append(label)

    for name in evidence.get('models', []):
        add(name in facts.models, f'model {name}')
    for name in evidence.get('fields', []):
        add(name in facts.fields, f'field {name}')
    for path in evidence.get('routes', []):
        add(path in facts.routes, f'endpoint {path}')
    for options in evidence.get('any_routes', []):
        add(any(p in facts.routes for p in options), f'endpoint {" or ".join(options)}')
    for name in evidence.get('symbols', []):
        add(name in facts.symbols, f'code {name}')
    for name in evidence.get('frontend', []):
        add(name in facts.frontend, f'screen part {name}')
    for (path, method), codename in evidence.get('route_perms', {}).items():
        route = facts.route(path)
        ok = bool(route and method in route.methods and route.required_permission(method) == codename)
        add(ok, f'{method.upper()} {path} needs {codename}')
    return have, missing


def rows():
    facts = Facts()
    out = []
    for group in (FR, NFR):
        for rid, text, priority, stories, rule in group:
            if isinstance(rule, tuple):
                status, note = rule
            else:
                have, missing = evaluate(rule, facts)
                status = 'Done' if not missing else ('Not built' if not have else 'Partly')
                note = '' if status == 'Done' else 'Not in the code yet: ' + ', '.join(missing)
            out.append((rid, text, priority, status, stories, note))
    return out


def table():
    data = rows()
    counts = {s: sum(1 for r in data if r[3] == s) for s in ('Done', 'Partly', 'Not built')}
    lines = ['| Req ID | Requirement | Priority | Status | Delivered by | Note |', '|---|---|---|---|---|---|']
    for rid, text, priority, status, stories, note in data:
        lines.append(f'| {rid} | {text} | {priority} | **{status}** | {stories} | {note} |')
    lines.append('')
    lines.append(f'*{len(data)} requirements: {counts["Done"]} Done, {counts["Partly"]} Partly, {counts["Not built"]} Not built. '
                 'Status is read from the code by `python manage.py generate_docs`.*')
    return '\n'.join(lines) + '\n'
