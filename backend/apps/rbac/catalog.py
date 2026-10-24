"""
The one list of every Permission in Ordinis.

Each entry: codename (what the code checks), name (shown on screen), module (the
section it is grouped under) and a plain-language description of what it allows.
`migrate` adds a missing Permission and refreshes names and descriptions from this
list (rbac.services.sync_permission_catalog), so adding a Permission means adding
one entry here and using its codename in a view. A test fails if a view demands a
codename that is not listed.
"""

PERMISSION_CATALOG = [
    # organization
    {"codename": "manage_departments", "name": "Manage Departments", "module": "organization",
     "description": "Create, rename and delete the company's Departments."},
    {"codename": "manage_designations", "name": "Manage Designations", "module": "organization",
     "description": "Create, rename and delete job titles (Designations). A title alone gives no access."},
    {"codename": "manage_employees", "name": "Manage Employees", "module": "organization",
     "description": "Add employees, edit who they report to, and remove them. Also shows the people summary on the dashboard."},
    # roles
    {"codename": "manage_roles", "name": "Manage Roles", "module": "roles",
     "description": "Create, edit and delete Roles and choose which Permissions each Role holds."},
    {"codename": "assign_roles", "name": "Assign Roles", "module": "roles",
     "description": "Give a Role to an employee or take it away."},
    # approvals
    {"codename": "manage_approval_chains", "name": "Manage Approval Chains", "module": "approvals",
     "description": "Design the steps a request such as leave passes through, and see every company request."},
    # tasks
    {"codename": "create_task", "name": "Create Tasks", "module": "tasks",
     "description": "Create tasks, assign them to employees, and review submitted work. Also shows the team summary on the dashboard."},
    # attendance
    {"codename": "manage_leave_types", "name": "Manage Leave Types", "module": "attendance",
     "description": "Define the kinds of leave the company offers and how many days a year each allows."},
    {"codename": "view_team_attendance", "name": "View Team Attendance", "module": "attendance",
     "description": "See any employee's attendance month by month. Without it, a manager still sees the people below them."},
    # payroll
    {"codename": "manage_finance", "name": "Manage Finance", "module": "payroll",
     "description": "See and change salary structures and generate payslips for everyone. Salary data is visible only with this Permission."},
    # tenants
    {"codename": "manage_company_settings", "name": "Manage Company Settings", "module": "tenants",
     "description": "Change company settings: currency, time zone, fiscal year start and language."},
    # audit_log
    {"codename": "view_audit_log", "name": "View Audit Log", "module": "audit_log",
     "description": "Read and export the company's audit log of who did what and when."},
    # analytics
    {"codename": "view_analytics", "name": "View Analytics", "module": "analytics",
     "description": "Open the Analytics page with attendance and task completion for the whole company."},
    # billing
    {"codename": "view_billing", "name": "View Billing", "module": "billing",
     "description": "See the company's plan, employee usage and invoices."},
    {"codename": "manage_billing", "name": "Manage Billing", "module": "billing",
     "description": "Choose a plan and a number of months, pay outside the system, submit the payment details, and read the company's own payments."},
    # platform_admin
    {"codename": "approve_support_access", "name": "Approve Support Access", "module": "platform_admin",
     "description": "Approve, deny or revoke the Ordinis team's time-limited, read-only access to the company, and read the access log."},
]

CATALOG_CODENAMES = {entry["codename"] for entry in PERMISSION_CATALOG}
