# Ordinis — Project Structure (as built)

The tree below is **generated from the actual folders** by `python manage.py generate_docs`; it lists only files that exist. A test fails when it drifts. The repository holds two folders, `backend` (Django + Django REST Framework) and `frontend` (React + Vite + Tailwind), plus `docs`.

<!-- BEGIN GENERATED:structure -->
```
backend/
  .env.example, manage.py, regression.py, requirements.txt
  config/   settings/ (base, development, production), urls.py, wsgi.py, asgi.py
  apps/
    accounts/  admin.py, apps.py, managers.py, models.py, serializers.py, urls.py, views.py, migrations/ (2)  (+ tests)
    approvals/  admin.py, apps.py, demo_data.py, models.py, serializers.py, services.py, urls.py, views.py, migrations/ (4), commands: start_demo_approval  (+ tests)
    attendance/  admin.py, apps.py, demo_data.py, leave_models.py, leave_serializers.py, leave_services.py, leave_views.py, models.py, serializers.py, services.py, urls.py, views.py, migrations/ (2)  (+ tests)
    core/  admin.py, api_matrix.py, apps.py, demo.py, doccheck.py, docgen.py, exceptions.py, mixins.py, models.py, pagination.py, permissions.py, serializer_utils.py, traceability.py, views.py, migrations/ (0), commands: check_docs, generate_docs, seed_demo_data  (+ tests)
    dashboard/  apps.py, services.py, urls.py, views.py  (+ tests)
    notifications/  apps.py, demo_data.py, models.py, serializers.py, services.py, signals.py, urls.py, views.py, migrations/ (1)  (+ tests)
    organization/  admin.py, apps.py, demo_data.py, models.py, serializers.py, services.py, urls.py, views.py, migrations/ (6)  (+ tests)
    payroll/  admin.py, apps.py, demo_data.py, models.py, serializers.py, services.py, urls.py, views.py, migrations/ (2)  (+ tests)
    platform_admin/  apps.py, demo_data.py, exceptions.py, models.py, serializers.py, services.py, urls.py, views.py, migrations/ (2), commands: create_platform_admin  (+ tests)
    rbac/  admin.py, apps.py, decorators.py, demo_data.py, models.py, serializers.py, services.py, urls.py, views.py, migrations/ (11)  (+ tests)
    tasks/  admin.py, apps.py, demo_data.py, models.py, serializers.py, services.py, urls.py, views.py, migrations/ (2)  (+ tests)
    tenants/  admin.py, apps.py, middleware.py, models.py, serializers.py, urls.py, views.py, migrations/ (1)  (+ tests)
  tests/   browser (Selenium) test files, selenium_helpers.py, selenium_runner.py

frontend/src/
    App.jsx, main.jsx
  components/common/  ChartCard.jsx, EmptyState.jsx, MetricCard.jsx, Pagination.jsx, PlanBadge.jsx, StatusPill.jsx
  components/dashboard/  StatCard.jsx
  components/layout/  Navbar.jsx, NotificationBell.jsx, Sidebar.jsx, navigation.js
  features/admin/  AccessRequestsPage.jsx, ActivityPage.jsx, CompaniesPage.jsx, TicketsPage.jsx, format.js, shared.jsx, usePagedList.js
  features/approvals/  ApprovalChainsPage.jsx, DelegationsPage.jsx, PendingApprovalsPage.jsx
  features/attendance/  AttendancePage.jsx
  features/auth/  LoginPage.jsx, RegisterPage.jsx
  features/dashboard/  DashboardPage.jsx, charts.jsx
  features/dev/  UiKitPage.jsx
  features/inbox/  ActionInboxPage.jsx, InboxIcon.jsx, kinds.js, timeAgo.js
  features/leave/  ApprovalProgress.jsx, LeavePage.jsx, LeaveTypesPage.jsx, leaveFormat.js
  features/organization/  DepartmentsPage.jsx, DesignationsPage.jsx, EmployeeDetailPage.jsx, EmployeesPage.jsx
  features/payroll/  MyPayslipsPage.jsx, PayslipViewPage.jsx, PayslipsPage.jsx, SalaryStructuresPage.jsx, payslipFormat.js
  features/platformAdmin/  SupportAccessPage.jsx
  features/roles/  EmployeeRolesPage.jsx, RolesPage.jsx
  features/tasks/  KanbanPage.jsx, TaskProgressPanel.jsx, TasksPage.jsx
  hooks/  useClickOutside.js
  layouts/  DashboardLayout.jsx
  routes/  AdminRoute.jsx, HomeRedirect.jsx, ProtectedRoute.jsx
  services/  adminService.js, apiClient.js, approvalsService.js, attendanceService.js, authService.js, dashboardService.js, leaveService.js, notificationsService.js, organizationService.js, paging.js, payrollService.js, rolesService.js, supportAccessService.js, tasksService.js
  store/  AuthContext.jsx
```
<!-- END GENERATED:structure -->

## How the code is organized

- **Backend apps** live in `backend/apps/`. Each app keeps HTTP handling in `views.py`, business rules in `services.py` (or a more specific `*_services.py`), the schema in `models.py`, and its tests next to it. Details and responsibilities are in SDS Section 5.
- **Demo data:** an app that has demo data adds `demo_data.py` (`ORDER` and `seed(ctx)`); `python manage.py seed_demo_data` finds it by itself.
- **Frontend:** `features/` has one folder per area, `services/` the API calls, `components/` the shared parts (`StatusPill`, `MetricCard`, `EmptyState`, `ChartCard`, `PlanBadge`, `Sidebar`, `Navbar`, `NotificationBell`), `routes/` the route guards, `layouts/` the shell, `store/` the login state.
- **Documents:** `docs/`. The files in `docs/generated/` are written by the command above; do not edit them by hand.

## Design decisions that differ from the first plan

| Area | First plan | As built | Why |
|---|---|---|---|
| Tenant isolation and permissions | Django middleware | DRF permission classes, applied by default (`DEFAULT_PERMISSION_CLASSES`) | The JWT user is resolved by DRF after the middleware chain, so middleware cannot see it. A default makes a forgotten permission safe |
| Roles app | `rbac` | `rbac` (Django app label `roles`) | The label was kept to avoid renaming migrations |
| Approvals for leave | a separate leave workflow | the same Approval Chain engine, through a finish handler | One engine for every approvable object |
| Task board | a status field only | a Kanban board with allowed moves and daily progress entries | Sprint 4 |
| Audit logging | `AuditLoggingMixin` on every write ViewSet | the mixin is in place but does nothing until the `audit_log` app exists (ST-135) | The app is a Sprint 5 story |

## Planned but not built (future work)

| Item | Status |
|---|---|
| `audit_log`, `analytics`, `billing` apps | Sprint 5 stories ST-135, ST-134, ST-136; they appear in the tree above once merged |
| Project, TaskComment, TaskAttachment, HolidayCalendar, Expense, Reimbursement | Not built |
| WebSocket notifications, Celery, Docker, CI/CD | Not built |
| Layer 3 apps (announcements, meetings, messaging, ...) | Not built; roadmap only |
