# Software Design Specification (SDS)

## Project Title

Ordinis — A Dynamic, Multi-Tenant Workflow & Chain-of-Command Configuration Platform

## Document Version

V1.0

## Date of Submission



## Team Info

| SL | Student ID | Student Name | Role |
|---|---|---|---|
| 1 |  | Saif |  |

---

# Document History

| Version | Date | Authors | Change Log | Approved By |
|---|---|---|---|---|
| V1.0 |  | Saif | Initial version — full architecture, data, component, interface, security, and deployment design |  |

# 1. Introduction

## 1.1 Purpose

This Software Design Specification (SDS) translates the requirements defined in the Ordinis Software Requirements Specification (SRS) into a concrete technical design: the system's architecture, data model, component breakdown, interfaces, security mechanisms, and deployment plan. Its intended audience is anyone who needs to understand **how** Ordinis is built, not just what it must do — primarily the developer (Saif) for implementation continuity across sessions, the course evaluator assessing design quality, and any future contributor extending the system.

## 1.2 Scope

This document covers the design of Ordinis as **delivered at the end of Sprint 5**: the Django REST Framework backend (12 apps) and the React (Vite) frontend consuming it. Parts of this document are read from the code and rewritten by `python manage.py generate_docs` (the data dictionary in 4.3, the API table in 6.3), so they always match the system; a test fails if they do not. Anything the SRS asks for that is not built is named as *future work* here and listed in SRS Section 7.2. Layer-3 extension modules (Meetings, Ticketing, Document Management, etc.) and Layer 4/5 items (AI features, mobile app, plugin marketplace) are outside this document; they are described only in the roadmap document.

## 1.3 Intended Audience

- **Developer (Saif)** — as an implementation reference and a continuity anchor across coding sessions
- **Course Evaluator** — to assess system architecture, data design, and design-principle adherence
- **Future Contributors** (Nexoria team, if the project continues commercially) — onboarding reference

## 1.4 References

- Ordinis Software Requirements Specification (`Ordinis_SRS.md`)
- Ordinis Project Proposal (`project-proposal.md`)
- Ordinis Final Idea Summary (`ordinis-final-idea.md`)
- Ordinis Master Build Prompt (`ordinis-master-prompt.md`)
- Ordinis Full ER Diagram (`ordinis-full-ER-diagram.md`, `ordinis-ER-diagram.md`)
- Ordinis Security Reference (`ordinis-security.md`)
- Ordinis Error Handling Reference (`ordinis-error-handling.md`)
- Ordinis Frontend Design System (`ordinis-frontend-design-system.md`)
- Ordinis Dashboard Design Reference (`ordinis-dashboard-design.md`)
- Ordinis Project Structure — as built (`ordinis-project-structure.md`, generated)
- Ordinis ER Diagram — as built (`ordinis-ER-diagram.md`, generated)
- Testing guide (`TESTING.md`)
- IEEE Std 1016, Software Design Description standard (general structural reference)

# 2. Design Overview

## 2.1 Design Goals

- **Scalability** — a single deployment must serve an arbitrary number of tenant companies, each with its own data volume, without cross-tenant interference
- **Maintainability** — adding a new module (e.g., a future Layer-3 feature) should not require touching unrelated modules
- **Security** — tenant isolation and permission-based access must be structurally impossible to bypass, not just conventionally followed
- **Performance** — dashboard and list views must stay responsive as a company's employee/task/attendance data grows
- **Availability** — the platform must remain usable for all unaffected tenants even if one company's data or a single background job misbehaves

## 2.2 Design Principles

- **Separation of Concerns** — HTTP request/response handling (`views.py`) is kept separate from business rules (`services.py`), which is kept separate from data access (`models.py`)
- **Modularity** — each business capability lives in its own Django app (12 apps), each with its own models/serializers/views/urls/services
- **Reusability** — shared behavior (UUID primary keys, timestamps, soft-delete, audit logging, tenant-active checks) is factored into a common `core` app and mixins, reused by every other app rather than duplicated
- **High Cohesion / Low Coupling** — apps depend on each other only through explicit foreign keys or imported service functions (e.g., `attendance` starts a leave request's approval through `approvals.services`), never through hidden global state
- **Data-Driven Configuration over Hardcoding** — organizational hierarchy, roles/permissions, and approval workflows are modeled as rows in the database, not as conditional logic in code, so a new tenant's structure requires zero code change

## 2.3 System Context

Ordinis sits between its end users (across six stakeholder classes — CEO, GM/AGM, Department Head, HR, Accountant, Employee — plus the platform-level Super Admin) and a single shared database, mediated entirely through a versioned REST API. There is no external system Ordinis currently integrates with; it is designed to **replace** the informal mix of Excel sheets, WhatsApp messages, and verbal communication that stakeholder interviews (see SRS Appendix B) confirmed is the current norm at target companies.

```
                        ┌─────────────────────────────┐
   Company A Users ───▶ │                             │
   (CEO/GM/HR/Emp.)      │                             │
                        │                             │
   Company B Users ───▶ │        ORDINIS PLATFORM     │ ◀── Platform Admin
   (CEO/GM/HR/Emp.)      │   (single shared deployment) │      (Break-Glass
                        │                             │       access only,
   Company C Users ───▶ │                             │       time-limited,
   (CEO/GM/HR/Emp.)      │                             │       fully logged)
                        └─────────────────────────────┘
                                     │
                                     ▼
                         Single PostgreSQL/SQLite DB
                    (every row scoped by company_id — Company
                     A's users can never see Company B's rows)
```

# 3. System Architecture

## 3.1 Architectural Overview

Ordinis follows a **layered, API-first, multi-tenant monolith** architecture — a single Django project containing 12 loosely-coupled apps, exposing a versioned REST API consumed by a separately-deployed React single-page application. It is a "monolith" deliberately, not microservices: at this scale, one deployable unit is simpler to build, test, and reason about within the course timeline, while the strict app-per-module boundary inside it keeps a future split into services possible later without a rewrite.

Within the backend, every request flows through four layers:

1. **Presentation/API layer** (`views.py`, DRF ViewSets) — parses the HTTP request, applies permission classes, delegates to the service layer, serializes the response
2. **Service layer** (`services.py`) — contains all business rules (leave-balance checking, payslip duplicate-prevention, task status-transition validation, hierarchy recursion, Break-Glass approval logic)
3. **Data access layer** (`models.py`, Django ORM) — defines the schema and simple model-level helpers (e.g., `Employee.has_permission()`)
4. **Cross-cutting concerns** — a closed-by-default permission policy (`DEFAULT_PERMISSION_CLASSES`: logged in and active company) and tenant filtering are applied to every ViewSet; audit logging is done once for every model by `audit_log` (signals plus a small middleware), so a new app is logged without any code

## 3.2 Architectural Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + Vite)                      │
│  ┌───────────┐  ┌──────────────┐  ┌───────────────────────────┐   │
│  │  Layouts   │  │   Features    │  │  services/apiClient.js    │   │
│  │ (role-wise)│  │ (per-module UI)│  │ (JWT auto-attach, axios) │   │
│  └───────────┘  └──────────────┘  └───────────────────────────┘   │
└───────────────────────────────┬────────────────────────────────────┘
                                 │ HTTPS / JSON  (/api/v1/...)
┌───────────────────────────────▼────────────────────────────────────┐
│                    BACKEND — Django REST Framework                 │
│                                                                     │
│  ┌───────────────── Presentation Layer (views.py) ───────────────┐ │
│  │  ViewSets · IsAuthenticated · IsCompanyActive · HasPermission │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                               ▼                                     │
│  ┌───────────────── Service Layer (services.py) ─────────────────┐ │
│  │  Business rules: leave balance, payslip idempotency, hierarchy │ │
│  │  recursion, task state machine, Break-Glass grant/expire logic │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
│                               ▼                                     │
│  ┌───────────────── Data Layer (models.py, Django ORM) ───────────┐ │
│  │  14 apps: core · tenants · accounts · organization · rbac ·    │ │
│  │  approvals · tasks · attendance · payroll · notifications ·    │ │
│  │  audit_log · analytics · billing · platform_admin              │ │
│  └───────────────────────────┬────────────────────────────────────┘ │
└───────────────────────────────┼─────────────────────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  SQLite (dev) /          │
                    │  PostgreSQL (production)  │
                    └─────────────────────────┘
```

## 3.3 Technology Stack

| Layer | Technology | Version / Notes |
|---|---|---|
| Frontend | React + Vite | Vite chosen over Next.js — login-gated internal dashboard, no SEO need |
| Frontend Styling | Tailwind CSS | "Modern Minimalist SaaS" design system (see `ordinis-frontend-design-system.md`) |
| Backend | Python + Django + Django REST Framework | Django 6.1, DRF 3.18 (exact versions in `backend/requirements.txt`) |
| Authentication | `djangorestframework-simplejwt` | JWT access + refresh token, embeds `email` + `company_id` |
| Database (dev) | SQLite | Local development only |
| Database (production target) | PostgreSQL | Not yet deployed; planned for production |
| Version Control | Git + GitHub (private) | `NexoriaHQ/ordinis` |
| Browser tests | Selenium 4 with Google Chrome | `python regression.py selenium`, see `TESTING.md` |
| Infrastructure (future work) | Docker + docker-compose, Celery + Redis, GitHub Actions CI/CD | Not built; not required for the course scope |

## 3.4 Deployment Architecture

**Current state (development):** Django development server (`runserver`) backed by local SQLite, run on Windows; frontend served by the Vite dev server (`http://localhost:5173`), calling the backend over `localhost`. A `seed_demo_data` command fills a demo company.

**Target state (production, post-course):** Containerized deployment — Django backend + PostgreSQL + Redis + Celery worker behind a WSGI server (Gunicorn), fronted by Nginx; React frontend built statically and served via a CDN/static host (e.g., Vercel) or the same Nginx layer. Both environments share the identical `/api/v1/` contract, so promoting from dev to production requires only environment/configuration changes, not code changes — a direct consequence of the environment-based settings split (`config/settings/development.py` vs `production.py`).

# 4. Data Design

## 4.1 Data Model Overview

Most models inherit from a shared `BaseModel` (in `core`) providing a UUID primary key, `created_at`/`updated_at` timestamps, and a soft-delete flag. Every tenant-scoped model carries a `company` foreign key (directly, or through `Employee`), which is the basis of multi-tenant isolation: every `get_queryset()` filters by the requesting user's company, and another company's object is a 404.

Three relationships are central to the design:

1. **`Employee.reports_to` (self-referencing FK)**: the organizational hierarchy is a tree stored in one column, so a 2-level startup and a 5-level enterprise use the same schema.
2. **`Role` ↔ `Permission` (Many-to-many) and `Employee` ↔ `Role` (`EmployeeRole`)**: keeps Designation (a label) and Role (a capability bundle) independent.
3. **`ApprovalInstance`'s `GenericForeignKey` (`content_type` + `object_id`)**: one approval engine serves a `LeaveRequest` today and any future approvable object without a new table per type. A module registers a finish handler (`approvals.services.register_finish_handler`) so its record follows the decision; leave does this in `attendance`.

## 4.2 Entity Relationship Diagram (ERD)

The ER diagram of the delivered system is generated from the real foreign keys and is in `ordinis-ER-diagram.md`. The full commercial vision (Project, TaskComment, TaskAttachment, HolidayCalendar, Expense, Reimbursement, AuditLog, CompanyHealthSnapshot, SubscriptionPlan, Subscription, Invoice and the Layer 3 modules) is `ordinis-full-ER-diagram.md` and is future work.

## 4.3 Data Dictionary

This section is **generated from the Django models** by `python manage.py generate_docs`. It lists every model and field of the delivered system and nothing else. A test (`core/test_docs_in_sync.py`) fails when it no longer matches the code.

<!-- BEGIN GENERATED:data-dictionary -->
Read from the Django models. Every model also has `id` (UUID, primary key), `created_at`, `updated_at` and `is_deleted` (from `core.BaseModel`) unless noted.

### App `accounts`

#### User

| Field | Type | Default | Notes |
|---|---|---|---|
| `password` | Char(128) |  |  |
| `last_login` | DateTime |  | can be empty (null) |
| `is_superuser` | Boolean | False |  |
| `company` | FK to tenants.Company |  | can be empty (null); on delete: CASCADE |
| `email` | Char(254) |  | unique |
| `full_name` | Char(150) | '' |  |
| `is_active` | Boolean | True |  |
| `is_staff` | Boolean | False |  |
| `is_platform_admin` | Boolean | False |  |
| `groups` | Many-to-many to Group | | |
| `user_permissions` | Many-to-many to Permission | | |

### App `analytics`

#### CompanyHealthSnapshot

One row per company and day: how healthy the company was on that day.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `date` | Date |  |  |
| `headcount` | PositiveInteger | 0 |  |
| `attendance_rate` | Decimal(4,1) | 0 |  |
| `task_completion_rate` | Decimal(4,1) | 0 |  |
| `open_tasks` | PositiveInteger | 0 |  |
| `overdue_tasks` | PositiveInteger | 0 |  |
| `health_score` | Decimal(4,1) | 0 |  |

Rule: `one_health_snapshot_per_company_per_day` (unique)

Rule: `snapshot_rates_0_to_100` (check)

### App `approvals`

#### ApprovalAction

One decision (approve/reject) on one step of an instance. Never edited or deleted.

| Field | Type | Default | Notes |
|---|---|---|---|
| `instance` | FK to approvals.ApprovalInstance |  | on delete: CASCADE |
| `step` | FK to approvals.ApprovalStep |  | can be empty (null); on delete: SET_NULL |
| `step_order` | PositiveInteger |  |  |
| `actor` | FK to organization.Employee |  | on delete: CASCADE |
| `decision` | Char(20) |  | one of: approved, rejected |
| `comment` | Text |  |  |

Rule: `unique_action_per_step` (unique)

#### ApprovalChain

A company-defined, ordered list of approval steps for one kind of request.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `name` | Char(100) |  |  |
| `applies_to_module` | Char(50) |  | one of: leave |

Rule: `unique_approval_chain_name_per_company` (unique)

#### ApprovalInstance

One live request travelling through a chain (e.g. a leave request).

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `approval_chain` | FK to approvals.ApprovalChain |  | on delete: PROTECT |
| `content_type` | FK to contenttypes.ContentType |  | on delete: CASCADE |
| `object_id` | UUID |  |  |
| `requested_by` | FK to organization.Employee |  | on delete: CASCADE |
| `current_step` | PositiveInteger | 1 |  |
| `status` | Char(20) | 'pending' | one of: pending, approved, rejected, cancelled |

#### ApprovalStep

One step of a chain. The step is approved by anyone holding `approver_role`.

| Field | Type | Default | Notes |
|---|---|---|---|
| `approval_chain` | FK to approvals.ApprovalChain |  | on delete: CASCADE |
| `step_order` | PositiveInteger |  |  |
| `approver_role` | FK to roles.Role |  | on delete: PROTECT |

Rule: `unique_step_order_per_chain` (unique)

#### DelegationRule

"While I am away, <delegate> may decide the requests that wait for my roles."

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `delegator` | FK to organization.Employee |  | on delete: CASCADE |
| `delegate` | FK to organization.Employee |  | on delete: CASCADE |
| `start_date` | Date |  |  |
| `end_date` | Date |  |  |
| `reason` | Char(255) |  |  |

Rule: `delegation_end_not_before_start` (check)

Rule: `delegation_not_to_self` (check)

### App `attendance`

#### Attendance

One row per employee per working day. `date` is the day in the COMPANY's own time

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `employee` | FK to organization.Employee |  | on delete: CASCADE |
| `date` | Date |  |  |
| `check_in` | DateTime |  |  |
| `check_out` | DateTime |  | can be empty (null) |

Rule: `one_attendance_per_employee_per_day` (unique)

#### LeaveRequest

One request for leave. It starts Pending. While it is Pending or Approved its days count against the

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `employee` | FK to organization.Employee |  | on delete: CASCADE |
| `leave_type` | FK to attendance.LeaveType |  | on delete: PROTECT |
| `start_date` | Date |  |  |
| `end_date` | Date |  |  |
| `days` | PositiveSmallInteger |  |  |
| `reason` | Char(500) |  |  |
| `status` | Char(20) | 'pending' | one of: pending, approved, rejected, cancelled |

Rule: `leave_end_not_before_start` (check)

#### LeaveType

A kind of leave a company offers, for example Annual or Sick, and how many days a year it allows.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `name` | Char(60) |  |  |
| `days_allowed_per_year` | PositiveSmallInteger | 0 |  |

Rule: `one_leave_type_name_per_company` (unique)

### App `audit_log`

#### AuditLog

One row for one sensitive action: who did what, to which record, in which company, and when.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | can be empty (null); on delete: SET_NULL |
| `company_name` | Char(255) |  |  |
| `actor` | FK to accounts.User |  | can be empty (null); on delete: SET_NULL |
| `actor_email` | Char(254) |  |  |
| `action` | Char(20) |  | one of: create, update, delete, read, export, denied |
| `status` | Char(10) | 'success' | one of: success, warning, failed |
| `module` | Char(50) |  |  |
| `model_name` | Char(100) |  |  |
| `object_id` | Char(64) |  |  |
| `object_repr` | Char(255) |  |  |
| `changed_fields` | JSON | list() |  |
| `ip_address` | GenericIPAddress |  | can be empty (null) |

### App `billing`

#### Invoice

A monthly bill. It keeps the amount of that day: a later plan change never alters an old invoice.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `subscription` | FK to billing.Subscription |  | on delete: CASCADE |
| `number` | Char(40) |  | unique |
| `plan_name` | Char(50) |  |  |
| `period_start` | Date |  |  |
| `period_end` | Date |  |  |
| `amount` | Decimal(10,2) |  |  |
| `currency` | Char(10) | 'BDT' |  |
| `status` | Char(10) | 'open' | one of: open, paid, void |
| `issued_on` | Date |  |  |
| `due_on` | Date |  |  |
| `paid_on` | Date |  | can be empty (null) |

Rule: `one_invoice_per_period` (unique)

Rule: `invoice_amount_not_negative` (check)

#### Subscription

The plan a company is on now. One per company.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | unique; on delete: CASCADE |
| `plan` | FK to billing.SubscriptionPlan |  | on delete: PROTECT |
| `status` | Char(20) | 'active' | one of: active, cancelled |
| `started_on` | Date |  |  |

#### SubscriptionPlan

A plan a company can be on. `max_employees` empty means unlimited.

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | Char(50) |  | unique |
| `max_employees` | PositiveInteger |  | can be empty (null) |
| `price_monthly` | Decimal(10,2) |  |  |
| `currency` | Char(10) | 'BDT' |  |
| `is_active` | Boolean | True |  |

Rule: `plan_price_not_negative` (check)

### App `notifications`

#### Notification

One message for ONE employee ("you were assigned a task", "an approval needs you").

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `recipient` | FK to organization.Employee |  | on delete: CASCADE |
| `kind` | Char(30) |  | one of: task_assigned, approval_requested, approval_decided |
| `title` | Char(200) |  |  |
| `message` | Char(500) |  |  |
| `link` | Char(200) |  |  |
| `is_read` | Boolean | False |  |
| `read_at` | DateTime |  | can be empty (null) |

### App `organization`

#### Department

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `name` | Char(100) |  |  |

#### Designation

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `title` | Char(100) |  |  |

#### Employee

| Field | Type | Default | Notes |
|---|---|---|---|
| `user` | FK to accounts.User |  | unique; on delete: CASCADE |
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `department` | FK to organization.Department |  | can be empty (null); on delete: SET_NULL |
| `designation` | FK to organization.Designation |  | can be empty (null); on delete: SET_NULL |
| `reports_to` | FK to organization.Employee |  | can be empty (null); on delete: SET_NULL |
| `employee_code` | Char(50) |  |  |
| `phone` | Char(30) | '' |  |
| `address` | Char(255) | '' |  |
| `emergency_contact_name` | Char(100) | '' |  |
| `emergency_contact_phone` | Char(30) | '' |  |
| `joined_on` | Date |  | can be empty (null) |

Rule: `unique_employee_code_per_company` (unique)

### App `payroll`

#### Payslip

One employee's pay for one month. A SNAPSHOT: the amounts are copied from the Salary Structure when the

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `employee` | FK to organization.Employee |  | on delete: CASCADE |
| `year` | PositiveSmallInteger |  |  |
| `month` | PositiveSmallInteger |  |  |
| `base_salary` | Decimal(12,2) |  |  |
| `allowances` | JSON | dict() |  |
| `gross_amount` | Decimal(12,2) |  |  |
| `deductions` | Decimal(12,2) | 0 |  |
| `deduction_note` | Char(255) |  |  |
| `net_amount` | Decimal(12,2) |  |  |
| `generated_by` | FK to organization.Employee |  | can be empty (null); on delete: SET_NULL |

Rule: `one_payslip_per_employee_month` (unique)

Rule: `payslip_month_1_to_12` (check)

Rule: `payslip_deductions_not_negative` (check)

Rule: `payslip_deductions_within_gross` (check)

#### SalaryStructure

The current pay structure of one employee: a base salary plus named allowances.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `employee` | FK to organization.Employee |  | unique; on delete: CASCADE |
| `base_salary` | Decimal(12,2) |  |  |
| `allowances` | JSON | dict() |  |

### App `platform_admin`

#### ImpersonationLog

One row per use of an approved grant. The company can read its own rows.

| Field | Type | Default | Notes |
|---|---|---|---|
| `access_request` | FK to platform_admin.SupportAccessRequest |  | on delete: CASCADE |
| `actor` | FK to accounts.User |  | on delete: PROTECT |
| `method` | Char(10) |  |  |
| `endpoint` | Char(255) |  |  |
| `detail` | Char(255) |  |  |

#### PlatformActionLog

What Platform Admins did to companies (suspend, activate, resolve a ticket). Kept even if the company is removed.

| Field | Type | Default | Notes |
|---|---|---|---|
| `actor` | FK to accounts.User |  | on delete: PROTECT |
| `company` | FK to tenants.Company |  | can be empty (null); on delete: SET_NULL |
| `company_name` | Char(255) |  |  |
| `action` | Char(40) |  |  |
| `note` | Char(255) |  |  |

#### SupportAccessRequest

Break-Glass: a Platform Admin asks ONE company for time-limited read access.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `requested_by` | FK to accounts.User |  | on delete: PROTECT |
| `reason` | Text |  |  |
| `status` | Char(20) | 'pending' | one of: pending, approved, denied, revoked |
| `decided_by` | FK to organization.Employee |  | can be empty (null); on delete: SET_NULL |
| `decided_at` | DateTime |  | can be empty (null) |
| `expires_at` | DateTime |  | can be empty (null) |

#### SupportTicket

A problem report a company's employee sends to Ordinis support.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `created_by` | FK to organization.Employee |  | can be empty (null); on delete: SET_NULL |
| `subject` | Char(200) |  |  |
| `description` | Text |  |  |
| `status` | Char(20) | 'open' | one of: open, resolved |
| `resolved_at` | DateTime |  | can be empty (null) |

### App `rbac`

#### EmployeeRole

Assignment of a Role to an Employee (an Employee can hold many Roles).

| Field | Type | Default | Notes |
|---|---|---|---|
| `employee` | FK to organization.Employee |  | on delete: CASCADE |
| `role` | FK to roles.Role |  | on delete: CASCADE |
| `company` | FK to tenants.Company |  | on delete: CASCADE |

Rule: `unique_employee_role_assignment` (unique)

#### Permission

System-wide permission (global — NOT company-scoped).

| Field | Type | Default | Notes |
|---|---|---|---|
| `codename` | Char(100) |  | unique |
| `name` | Char(255) |  |  |
| `module` | Char(50) |  |  |
| `description` | Char(500) | '' |  |

#### Role

Company-scoped role — a named collection of permissions.

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `name` | Char(100) |  |  |
| `description` | Text |  |  |
| `is_system_default` | Boolean | False |  |
| `permissions` | Many-to-many to Permission | | |

Rule: unique together: company, name

### App `tasks`

#### Task

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | on delete: CASCADE |
| `title` | Char(200) |  |  |
| `description` | Text |  |  |
| `assigned_to` | FK to organization.Employee |  | on delete: CASCADE |
| `assigned_by` | FK to organization.Employee |  | can be empty (null); on delete: SET_NULL |
| `priority` | Char(10) | 'medium' | one of: low, medium, high |
| `deadline` | Date |  | can be empty (null) |
| `status` | Char(20) | 'not_started' | one of: not_started, in_progress, submitted, completed, rejected |

#### TaskProgressLog

One daily progress note on a task, written by the assignee.

| Field | Type | Default | Notes |
|---|---|---|---|
| `task` | FK to tasks.Task |  | on delete: CASCADE |
| `employee` | FK to organization.Employee |  | on delete: CASCADE |
| `date` | Date |  |  |
| `update_text` | Text |  |  |
| `progress_percent` | PositiveSmallInteger |  |  |
| `blocker_text` | Char(500) |  |  |
| `external_reference_url` | Char(500) |  |  |

### App `tenants`

#### Company

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | Char(255) |  |  |
| `subdomain` | Slug |  | unique |
| `logo` | Char(200) |  | can be empty (null) |
| `industry` | Char(100) |  |  |
| `is_active` | Boolean | True |  |

#### CompanySettings

| Field | Type | Default | Notes |
|---|---|---|---|
| `company` | FK to tenants.Company |  | unique; on delete: CASCADE |
| `currency` | Char(10) | 'BDT' |  |
| `timezone` | Char(50) | 'Asia/Dhaka' |  |
| `fiscal_year_start` | Char(10) | '01-01' |  |
| `default_language` | Char(10) | 'en' |  |

*31 models.*
<!-- END GENERATED:data-dictionary -->

## 4.4 Data Storage & Retention

- **Development:** SQLite file (`db.sqlite3`), rebuilt from migrations as needed.
- **Production target:** PostgreSQL (planned; not deployed). The schema has not been tested on PostgreSQL.
- **Soft delete:** `BaseModel` provides a soft-delete flag. Approval actions, progress entries, and platform logs have no edit or delete endpoint.
- **Audit log:** `AuditLog` is append-only (the model refuses update and delete; the API has no write endpoint). It keeps only the names of changed fields, never their values, and its rows outlive a deleted company, user or employee (`SET_NULL` with name snapshots). Break-Glass reads are also in `ImpersonationLog` and platform admin actions in `PlatformActionLog`.
- **Retention policy:** not defined; no automatic purge exists. All data persists until removed manually.

# 5. Component Design

## 5.1 Component Overview

| Component | Description | Responsibility |
|---|---|---|
| core | Shared foundation | `BaseModel`, standard response envelope and exception handler, permission classes (`IsCompanyActive`, `HasPermission`, `IsHierarchySuperior`, `IsPlatformAdmin`), pagination, the demo-data command, the documentation generator and checker |
| tenants | Tenant management | Company and company settings (currency, time zone, fiscal year) |
| accounts | Identity and auth | Custom `User`, JWT login/refresh/logout, atomic company self-registration, "who am I" |
| organization | Hierarchy engine | Department, Designation, Employee CRUD; recursive subordinate and manager resolution |
| rbac | Access control | Permission catalog, Role, EmployeeRole; `PermissionRequiredMixin` |
| approvals | Workflow engine | Approval Chain, Step, Instance, Action; Delegation Rule; finish handlers |
| tasks | Task management | Task CRUD, Kanban board, status moves, daily progress entries |
| attendance | Attendance and leave | Check-in/out, monthly calendar, Leave Types, leave requests with balance check, approval through the Approval Chain |
| payroll | Payroll | Salary Structure, Payslip generation (no duplicates) |
| notifications | Alerts and inbox | Notifications for task assignment and approvals; the Action Inbox |
| dashboard | Role dashboards | One summary endpoint; sections depend on the user's Permissions |
| analytics | Company health | Read-only overview (attendance rate, task completion, overdue tasks, workload, tasks by department); daily Company Health Snapshot |
| platform_admin | Platform operation | Company list, suspend/activate, support tickets, Break-Glass access requests, access log |

## 5.2 Detailed Component Design

### `organization` (Hierarchy Engine)

- **Purpose:** model and query an arbitrary-depth organizational tree without hardcoded levels.
- **Internal logic:** `services.py` has `get_all_subordinates(employee)` and `get_all_managers(employee)`, walking the `reports_to` self-FK. A save that would create a cycle is refused. An employee who still has a team, the last CEO-role holder, and yourself cannot be deleted.

### `rbac` (Access Control)

- **Purpose:** decouple "what job title someone has" from "what they are allowed to do".
- **Internal logic:** `Employee.has_permission(codename)` checks `EmployeeRole → Role → Permission`. `PermissionRequiredMixin` (`rbac/decorators.py`) lets a ViewSet declare `permission_required` (one codename, or one per action) and rejects the request with 403 when the employee lacks it. The CEO's system Role cannot be edited or deleted and receives every new Permission.

### `approvals` (Workflow Engine)

- **Purpose:** let a company define its own multi-step approval for any approvable object.
- **Internal logic:** `ApprovalInstance` attaches to any model through `GenericForeignKey`. `decide()` records an `ApprovalAction`, advances `current_step`, and when the last step is approved (or any step is rejected) sets the final status and runs the owning module's finish handler in the same transaction. A request cannot be decided by its own requester, twice on one step, or by someone without the step's Role (or an active delegation). A chain with pending requests cannot be edited.

**Leave approval flow:**

```
Employee           attendance (apply_leave)        approvals            Approver
   │ POST leave-requests/ │                            │                    │
   │─────────────────────▶│ balance check              │                    │
   │                      │ choose the chain           │                    │
   │                      │ start_approval ───────────▶│ step 1 notified    │
   │  201 (Pending)       │                            │───────────────────▶│
   │◀─────────────────────│                            │   approve / reject │
   │                      │◀── finish handler ─────────│◀───────────────────│
   │   leave Approved or Rejected, Notification to the Employee             │
```

The chain is the company's first leave chain whose every step has an approver other than the applicant. Otherwise a default chain "Leave Approval (default)" (one step, the CEO role) is created once and used, so a request is never stuck. If not even the CEO can decide (the applicant is the only CEO), the request is refused with `LEAVE_NO_APPROVER`.

### `tasks` (Task Management)

- **Purpose:** tasks only move through valid states, and work is visible without file uploads.
- **Internal logic:** `services.py` has `check_transition`, `start_task`, `submit_task`, `move_task` (the Kanban move, with who may do which move), `add_progress` (text, percent, optional blocker and link, dated by the server) and `build_board` (four columns with counts). A rejected task sits in To Do with a rejected flag.

### `payroll` (Payroll)

- **Purpose:** compute payslips reliably and prevent double payment.
- **Internal logic:** `generate_payslip()` reads the Employee's `SalaryStructure`, computes gross, deductions and net, refuses a future month and a duplicate (`PayslipError`), and is backed by a database unique constraint. A payslip is a snapshot: later salary changes do not touch it. An employee sees only their own payslips unless they hold the finance Permission.

### `analytics` (Company Health)

- **Purpose:** show the CEO how healthy the company is, from the company's own attendance and task rows only.
- **Internal logic:** `services.overview()` returns the four metric numbers and the data of two charts (attendance rate for the last 6 months, completed and pending tasks per department). A *working day* is a day on which at least one employee checked in, so the company's own week and holidays are followed without a setting. Attendance rate = present employee-days / (employees x working days - employee-days on Approved leave without a check-in), never above 100; a month with no working day is 0. The head count used is the one today. `take_snapshot()` stores one `CompanyHealthSnapshot` per company and day (`python manage.py take_health_snapshots`, safe to run twice); a page load never writes. Both endpoints need the Permission `view_analytics`, which the CEO role receives automatically.

### `attendance` (Monthly Calendar)

- **Purpose:** let an employee see their own month at a glance (ST-137).
- **Internal logic:** `services.month_calendar(employee, month)` gives a status for every day plus the month's summary, for the logged-in employee only (the endpoint takes no employee id). A day is *Present* with a check-in; otherwise it has no status if nobody in the company checked in that day (a weekend or holiday, because no Holiday Calendar exists) or if it is after today; otherwise *On Leave* when an Approved leave covers it, no status yet for today (the day is not over), and *Absent* for every other day. Attendance rate = present / (present + absent); leave days are not expected. Limit: a day on which someone works a weekend shows *Absent* for the others.

### `platform_admin` (Break-Glass Access)

- **Purpose:** let the platform operator help a client without ever having default access to that client's data.
- **Internal logic:** the Platform Admin sends a `SupportAccessRequest` with a reason. The company's CEO (or a holder of `approve_support_access`) approves for 1 to 72 hours, denies, or revokes. While approved, the admin gets read-only access to a short list of resources (salary and payroll are never offered); every read is written to `ImpersonationLog`. Access ends by itself at `expires_at`. Suspend/activate and ticket actions are recorded in `PlatformActionLog`. A token issued before a suspension stops working.

**Break-Glass flow:**

```
Platform Admin     SupportAccessRequest API        Company CEO
     │ POST requests/ (reason)         │                │
     │────────────────────────────────▶│ pending        │
     │                                 │───────────────▶│ reviews
     │                                 │◀───────────────│ approve (1-72 h)
     │ read-only access until expires_at; every read -> ImpersonationLog
     │ expires by itself, or the CEO revokes it
```

# 6. Interface Design

## 6.1 User Interface Design

**Design system in force:** "Modern Minimalist SaaS" (`ordinis-frontend-design-system.md`): navy `#14142B` and violet `#6C31D6` on an off-white background, subtle 150-300 ms animation, Tailwind CSS. The approved mockup set has been implemented for the screens below.

**Screens built:** Login and Register; role Dashboards (CEO, Manager, HR, Accountant, Employee sections chosen by Permission); Departments, Designations, Employees and Employee detail (with subordinates and roles); Roles and Employee roles; Approval Chains, Pending Approvals, Delegations; Tasks list and Kanban board with progress entries; Attendance (check-in/out and a monthly calendar with Present, Absent, On Leave and rate cards) and Leave (apply, balance, cancel, approval progress) and Leave Types; Action Inbox; Analytics (metric cards, attendance line chart, tasks-by-department bar chart); Payslips, My Payslips, Payslip view, Salary Structures; Support Access (company side of Break-Glass); platform Admin screens (Companies, Tickets, Access Requests, Activity); a UI-kit showcase at `/dev/ui-kit` in development.

**Shell:** a grouped, collapsible sidebar (an item is hidden when the user lacks its Permission), a top bar with page title, search, company name, notification bell and user menu, and a plan badge that shows only what the server sends.

**Not built (future work):** a company switcher with more than one company.

- **Accessibility:** status is shown by colour and text together (`StatusPill`), never colour alone; sufficient contrast between navy/violet text and the off-white background; controls sized for mouse and touch.
- **Figma:** not produced; the accepted screenshot set served as the reference.

## 6.2 External Interfaces

None. Ordinis calls no third-party API or payment gateway (payment gateways are future work).

## 6.3 API Design

All endpoints are under `/api/v1/`, return JSON, and use one envelope: `{success, data, message}` on success or `{success, error: {code, message, field_errors}}` on failure. Every endpoint needs a login except login, refresh, logout and register. Every list is paginated (page size 20, up to 100 with `?page_size=`). The table below is **generated from the URL configuration** by `python manage.py generate_docs`: it contains every endpoint and nothing else, and a test fails if it drifts. "Who" is the Permission the server checks; "Any logged-in employee" means the view checks only the login and the service then checks ownership (assignee, approver, record owner).

<!-- BEGIN GENERATED:api-table -->
Every endpoint under `/api/v1/`, read from the URL configuration. `{id}` is a record id. "Who" is what the server checks: a Permission codename, or only a login (the service then checks ownership, for example the assignee or the approver).

| Method | Endpoint | View / action | Who |
|---|---|---|---|
| GET | `/api/v1/analytics/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/analytics/overview/` | OverviewViewSet / list | Permission `view_analytics` |
| GET | `/api/v1/analytics/snapshots/` | SnapshotViewSet / list | Permission `view_analytics` |
| GET | `/api/v1/approvals/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/approvals/chains/` | ApprovalChainViewSet / list | Any logged-in employee |
| POST | `/api/v1/approvals/chains/` | ApprovalChainViewSet / create | Permission `manage_approval_chains` |
| GET | `/api/v1/approvals/chains/{id}/` | ApprovalChainViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/approvals/chains/{id}/` | ApprovalChainViewSet / update | Permission `manage_approval_chains` |
| PATCH | `/api/v1/approvals/chains/{id}/` | ApprovalChainViewSet / partial_update | Permission `manage_approval_chains` |
| DELETE | `/api/v1/approvals/chains/{id}/` | ApprovalChainViewSet / destroy | Permission `manage_approval_chains` |
| POST | `/api/v1/approvals/chains/{id}/reorder/` | ApprovalChainViewSet / reorder | Permission `manage_approval_chains` |
| GET | `/api/v1/approvals/delegations/` | DelegationRuleViewSet / list | Any logged-in employee |
| POST | `/api/v1/approvals/delegations/` | DelegationRuleViewSet / create | Any logged-in employee |
| GET | `/api/v1/approvals/delegations/{id}/` | DelegationRuleViewSet / retrieve | Any logged-in employee |
| DELETE | `/api/v1/approvals/delegations/{id}/` | DelegationRuleViewSet / destroy | Any logged-in employee |
| GET | `/api/v1/approvals/instances/` | ApprovalInstanceViewSet / list | Any logged-in employee |
| GET | `/api/v1/approvals/instances/{id}/` | ApprovalInstanceViewSet / retrieve | Any logged-in employee |
| POST | `/api/v1/approvals/instances/{id}/approve/` | ApprovalInstanceViewSet / approve | Any logged-in employee |
| POST | `/api/v1/approvals/instances/{id}/reject/` | ApprovalInstanceViewSet / reject | Any logged-in employee |
| GET | `/api/v1/approvals/steps/` | ApprovalStepViewSet / list | Any logged-in employee |
| POST | `/api/v1/approvals/steps/` | ApprovalStepViewSet / create | Permission `manage_approval_chains` |
| GET | `/api/v1/approvals/steps/{id}/` | ApprovalStepViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/approvals/steps/{id}/` | ApprovalStepViewSet / update | Permission `manage_approval_chains` |
| PATCH | `/api/v1/approvals/steps/{id}/` | ApprovalStepViewSet / partial_update | Permission `manage_approval_chains` |
| DELETE | `/api/v1/approvals/steps/{id}/` | ApprovalStepViewSet / destroy | Permission `manage_approval_chains` |
| GET | `/api/v1/attendance/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/attendance/attendance/` | AttendanceViewSet / list | Any logged-in employee |
| GET | `/api/v1/attendance/attendance/calendar/` | AttendanceViewSet / calendar | Any logged-in employee |
| POST | `/api/v1/attendance/attendance/check_in/` | AttendanceViewSet / check_in | Any logged-in employee |
| POST | `/api/v1/attendance/attendance/check_out/` | AttendanceViewSet / check_out | Any logged-in employee |
| GET | `/api/v1/attendance/attendance/today/` | AttendanceViewSet / today | Any logged-in employee |
| GET | `/api/v1/attendance/attendance/{id}/` | AttendanceViewSet / retrieve | Any logged-in employee |
| GET | `/api/v1/attendance/leave-requests/` | LeaveRequestViewSet / list | Any logged-in employee |
| POST | `/api/v1/attendance/leave-requests/` | LeaveRequestViewSet / create | Any logged-in employee |
| GET | `/api/v1/attendance/leave-requests/balance/` | LeaveRequestViewSet / balance | Any logged-in employee |
| GET | `/api/v1/attendance/leave-requests/{id}/` | LeaveRequestViewSet / retrieve | Any logged-in employee |
| POST | `/api/v1/attendance/leave-requests/{id}/cancel/` | LeaveRequestViewSet / cancel | Any logged-in employee |
| GET | `/api/v1/attendance/leave-types/` | LeaveTypeViewSet / list | Any logged-in employee |
| POST | `/api/v1/attendance/leave-types/` | LeaveTypeViewSet / create | Permission `manage_leave_types` |
| GET | `/api/v1/attendance/leave-types/{id}/` | LeaveTypeViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/attendance/leave-types/{id}/` | LeaveTypeViewSet / update | Permission `manage_leave_types` |
| PATCH | `/api/v1/attendance/leave-types/{id}/` | LeaveTypeViewSet / partial_update | Permission `manage_leave_types` |
| DELETE | `/api/v1/attendance/leave-types/{id}/` | LeaveTypeViewSet / destroy | Permission `manage_leave_types` |
| GET | `/api/v1/audit-log/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/audit-log/logs/` | AuditLogViewSet / list | Permission `view_audit_log` |
| GET | `/api/v1/audit-log/logs/export/` | AuditLogViewSet / export | Permission `view_audit_log` |
| GET | `/api/v1/audit-log/logs/modules/` | AuditLogViewSet / modules | Permission `view_audit_log` |
| GET | `/api/v1/audit-log/logs/{id}/` | AuditLogViewSet / retrieve | Permission `view_audit_log` |
| POST | `/api/v1/auth/login/` | CustomTokenObtainPairView | Public |
| POST | `/api/v1/auth/logout/` | TokenBlacklistView | Public |
| GET | `/api/v1/auth/me/` | MeView | Any logged-in employee |
| GET | `/api/v1/auth/profile/` | ProfileView | Any logged-in employee |
| PATCH | `/api/v1/auth/profile/` | ProfileView | Any logged-in employee |
| POST | `/api/v1/auth/refresh/` | TokenRefreshView | Public |
| POST | `/api/v1/auth/register/` | CompanyRegisterView | Public |
| GET | `/api/v1/billing/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/billing/invoices/` | InvoiceViewSet / list | Permission `view_billing` |
| GET | `/api/v1/billing/invoices/{id}/` | InvoiceViewSet / retrieve | Permission `view_billing` |
| GET | `/api/v1/billing/plans/` | PlanViewSet / list | Permission `view_billing` |
| GET | `/api/v1/billing/subscription/` | SubscriptionViewSet / list | Permission `view_billing` |
| GET | `/api/v1/dashboard/summary/` | DashboardSummaryView | Any logged-in employee |
| GET | `/api/v1/notifications/` | NotificationViewSet / list | Any logged-in employee |
| GET | `/api/v1/notifications/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/notifications/inbox/` | NotificationViewSet / inbox | Any logged-in employee |
| GET | `/api/v1/notifications/inbox/summary/` | NotificationViewSet / inbox_summary | Any logged-in employee |
| POST | `/api/v1/notifications/read-all/` | NotificationViewSet / read_all | Any logged-in employee |
| GET | `/api/v1/notifications/{id}/` | NotificationViewSet / retrieve | Any logged-in employee |
| POST | `/api/v1/notifications/{id}/read/` | NotificationViewSet / read | Any logged-in employee |
| GET | `/api/v1/organization/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/organization/departments/` | DepartmentViewSet / list | Any logged-in employee |
| POST | `/api/v1/organization/departments/` | DepartmentViewSet / create | Permission `manage_departments` |
| GET | `/api/v1/organization/departments/{id}/` | DepartmentViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/organization/departments/{id}/` | DepartmentViewSet / update | Permission `manage_departments` |
| PATCH | `/api/v1/organization/departments/{id}/` | DepartmentViewSet / partial_update | Permission `manage_departments` |
| DELETE | `/api/v1/organization/departments/{id}/` | DepartmentViewSet / destroy | Permission `manage_departments` |
| GET | `/api/v1/organization/designations/` | DesignationViewSet / list | Any logged-in employee |
| POST | `/api/v1/organization/designations/` | DesignationViewSet / create | Permission `manage_designations` |
| GET | `/api/v1/organization/designations/{id}/` | DesignationViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/organization/designations/{id}/` | DesignationViewSet / update | Permission `manage_designations` |
| PATCH | `/api/v1/organization/designations/{id}/` | DesignationViewSet / partial_update | Permission `manage_designations` |
| DELETE | `/api/v1/organization/designations/{id}/` | DesignationViewSet / destroy | Permission `manage_designations` |
| GET | `/api/v1/organization/employees/` | EmployeeViewSet / list | Any logged-in employee |
| POST | `/api/v1/organization/employees/` | EmployeeViewSet / create | Permission `manage_employees` |
| GET | `/api/v1/organization/employees/{id}/` | EmployeeViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/organization/employees/{id}/` | EmployeeViewSet / update | Permission `manage_employees` |
| PATCH | `/api/v1/organization/employees/{id}/` | EmployeeViewSet / partial_update | Permission `manage_employees` |
| DELETE | `/api/v1/organization/employees/{id}/` | EmployeeViewSet / destroy | Permission `manage_employees` |
| GET | `/api/v1/organization/employees/{id}/subordinates/` | EmployeeViewSet / subordinates | Any logged-in employee |
| GET | `/api/v1/payroll/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/payroll/payslips/` | PayslipViewSet / list | Any logged-in employee |
| POST | `/api/v1/payroll/payslips/` | PayslipViewSet / create | Permission `manage_finance` |
| GET | `/api/v1/payroll/payslips/{id}/` | PayslipViewSet / retrieve | Any logged-in employee |
| DELETE | `/api/v1/payroll/payslips/{id}/` | PayslipViewSet / destroy | Permission `manage_finance` |
| GET | `/api/v1/payroll/salary-structures/` | SalaryStructureViewSet / list | Permission `manage_finance` |
| POST | `/api/v1/payroll/salary-structures/` | SalaryStructureViewSet / create | Permission `manage_finance` |
| GET | `/api/v1/payroll/salary-structures/{id}/` | SalaryStructureViewSet / retrieve | Permission `manage_finance` |
| PUT | `/api/v1/payroll/salary-structures/{id}/` | SalaryStructureViewSet / update | Permission `manage_finance` |
| PATCH | `/api/v1/payroll/salary-structures/{id}/` | SalaryStructureViewSet / partial_update | Permission `manage_finance` |
| DELETE | `/api/v1/payroll/salary-structures/{id}/` | SalaryStructureViewSet / destroy | Permission `manage_finance` |
| GET | `/api/v1/platform-admin/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/platform-admin/admin/access-requests/` | AdminAccessRequestViewSet / list | Platform Admin |
| GET | `/api/v1/platform-admin/admin/actions/` | AdminActionLogViewSet / list | Platform Admin |
| GET | `/api/v1/platform-admin/admin/companies/` | AdminCompanyViewSet / list | Platform Admin |
| POST | `/api/v1/platform-admin/admin/companies/{id}/activate/` | AdminCompanyViewSet / activate | Platform Admin |
| POST | `/api/v1/platform-admin/admin/companies/{id}/suspend/` | AdminCompanyViewSet / suspend | Platform Admin |
| GET | `/api/v1/platform-admin/admin/tickets/` | AdminTicketViewSet / list | Platform Admin |
| GET | `/api/v1/platform-admin/admin/tickets/{id}/` | AdminTicketViewSet / retrieve | Platform Admin |
| POST | `/api/v1/platform-admin/admin/tickets/{id}/reopen/` | AdminTicketViewSet / reopen | Platform Admin |
| POST | `/api/v1/platform-admin/admin/tickets/{id}/resolve/` | AdminTicketViewSet / resolve | Platform Admin |
| GET | `/api/v1/platform-admin/company/access-log/` | CompanyAccessLogViewSet / list | Permission `approve_support_access` |
| GET | `/api/v1/platform-admin/company/access-log/{id}/` | CompanyAccessLogViewSet / retrieve | Permission `approve_support_access` |
| GET | `/api/v1/platform-admin/company/access-requests/` | CompanyAccessRequestViewSet / list | Permission `approve_support_access` |
| GET | `/api/v1/platform-admin/company/access-requests/{id}/` | CompanyAccessRequestViewSet / retrieve | Permission `approve_support_access` |
| POST | `/api/v1/platform-admin/company/access-requests/{id}/approve/` | CompanyAccessRequestViewSet / approve | Permission `approve_support_access` |
| POST | `/api/v1/platform-admin/company/access-requests/{id}/deny/` | CompanyAccessRequestViewSet / deny | Permission `approve_support_access` |
| POST | `/api/v1/platform-admin/company/access-requests/{id}/revoke/` | CompanyAccessRequestViewSet / revoke | Permission `approve_support_access` |
| GET | `/api/v1/platform-admin/company/tickets/` | CompanyTicketViewSet / list | Any logged-in employee |
| POST | `/api/v1/platform-admin/company/tickets/` | CompanyTicketViewSet / create | Any logged-in employee |
| GET | `/api/v1/platform-admin/company/tickets/{id}/` | CompanyTicketViewSet / retrieve | Any logged-in employee |
| GET | `/api/v1/platform-admin/requests/` | PlatformAccessRequestViewSet / list | Platform Admin |
| POST | `/api/v1/platform-admin/requests/` | PlatformAccessRequestViewSet / create | Platform Admin |
| GET | `/api/v1/platform-admin/requests/{id}/` | PlatformAccessRequestViewSet / retrieve | Platform Admin |
| GET | `/api/v1/platform-admin/support/{company_id}/{resource}/` | SupportDataView | Platform Admin |
| GET | `/api/v1/rbac/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/rbac/employee-roles/` | EmployeeRoleViewSet / list | Any logged-in employee |
| POST | `/api/v1/rbac/employee-roles/` | EmployeeRoleViewSet / create | Permission `assign_roles` |
| GET | `/api/v1/rbac/employee-roles/{id}/` | EmployeeRoleViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/rbac/employee-roles/{id}/` | EmployeeRoleViewSet / update | Permission `assign_roles` |
| PATCH | `/api/v1/rbac/employee-roles/{id}/` | EmployeeRoleViewSet / partial_update | Permission `assign_roles` |
| DELETE | `/api/v1/rbac/employee-roles/{id}/` | EmployeeRoleViewSet / destroy | Permission `assign_roles` |
| GET | `/api/v1/rbac/permissions/` | PermissionViewSet / list | Any logged-in employee |
| GET | `/api/v1/rbac/roles/` | RoleViewSet / list | Any logged-in employee |
| POST | `/api/v1/rbac/roles/` | RoleViewSet / create | Permission `manage_roles` |
| GET | `/api/v1/rbac/roles/{id}/` | RoleViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/rbac/roles/{id}/` | RoleViewSet / update | Permission `manage_roles` |
| PATCH | `/api/v1/rbac/roles/{id}/` | RoleViewSet / partial_update | Permission `manage_roles` |
| DELETE | `/api/v1/rbac/roles/{id}/` | RoleViewSet / destroy | Permission `manage_roles` |
| GET | `/api/v1/tasks/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/tasks/tasks/` | TaskViewSet / list | Any logged-in employee |
| POST | `/api/v1/tasks/tasks/` | TaskViewSet / create | Permission `create_task` |
| GET | `/api/v1/tasks/tasks/board/` | TaskViewSet / board | Any logged-in employee |
| GET | `/api/v1/tasks/tasks/{id}/` | TaskViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/tasks/tasks/{id}/` | TaskViewSet / update | Permission `create_task` |
| PATCH | `/api/v1/tasks/tasks/{id}/` | TaskViewSet / partial_update | Permission `create_task` |
| DELETE | `/api/v1/tasks/tasks/{id}/` | TaskViewSet / destroy | Permission `create_task` |
| POST | `/api/v1/tasks/tasks/{id}/move/` | TaskViewSet / move | Any logged-in employee |
| GET | `/api/v1/tasks/tasks/{id}/progress/` | TaskViewSet / progress | Any logged-in employee |
| POST | `/api/v1/tasks/tasks/{id}/progress/` | TaskViewSet / progress | Any logged-in employee |
| POST | `/api/v1/tasks/tasks/{id}/start/` | TaskViewSet / start | Any logged-in employee |
| POST | `/api/v1/tasks/tasks/{id}/submit/` | TaskViewSet / submit | Any logged-in employee |
| GET | `/api/v1/tenants/` | APIRootView | Any logged-in employee |
| GET | `/api/v1/tenants/company/` | CompanyViewSet / list | Any logged-in employee |
| GET | `/api/v1/tenants/company/{id}/` | CompanyViewSet / retrieve | Any logged-in employee |
| GET | `/api/v1/tenants/settings/` | CompanySettingsViewSet / list | Any logged-in employee |
| GET | `/api/v1/tenants/settings/{id}/` | CompanySettingsViewSet / retrieve | Any logged-in employee |
| PUT | `/api/v1/tenants/settings/{id}/` | CompanySettingsViewSet / update | Permission `manage_company_settings` |
| PATCH | `/api/v1/tenants/settings/{id}/` | CompanySettingsViewSet / partial_update | Permission `manage_company_settings` |

*157 endpoint methods on 106 routes.*
<!-- END GENERATED:api-table -->

## 6.4 Hardware Interfaces

Not applicable. Ordinis requires no dedicated or proprietary hardware; it runs on standard server hardware/cloud VMs and is accessed from standard client devices.

## 6.5 Communication Interfaces

- **Protocol:** HTTPS (HTTP in local development only)
- **Message format:** JSON request/response bodies throughout
- **Authentication header:** `Authorization: Bearer <JWT access token>` on every protected request
- **Real-time channel:** none; the Action Inbox and the notification bell fetch on demand (WebSockets are future work)

# 7. Security Design

## 7.1 Authentication & Authorization

- **Authentication:** stateless JWT (`djangorestframework-simplejwt`): access token 15 minutes, refresh token 7 days, rotated on use, the old one blacklisted; logout blacklists the refresh token. A user of a suspended company cannot log in and an already-issued token stops working.
- **Closed by default:** `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` is "logged in" plus `IsCompanyActive` (the company is not suspended). A view that forgets `permission_classes` is closed, not open; only login, refresh, logout and register opt out. This was found and fixed in Sprint 5 by the endpoint matrix test.
- **Authorization at two independent levels:** (1) tenant isolation: every queryset is filtered by company and another company's object is a 404; (2) Permission: `PermissionRequiredMixin` checks a specific codename, never a Designation or a login alone. Platform Admin endpoints require `IsPlatformAdmin` and refuse company users.
- **Why not Django middleware:** the JWT user is resolved by DRF after the middleware chain, so `request.user` is still anonymous there. This is why tenant and permission checks are DRF permission classes.

## 7.2 Data Security

- **In transit:** HTTPS is required in production; not configured in development.
- **Passwords:** Django's default PBKDF2 hasher; plaintext is never stored. A fast hasher is used only while tests run.
- **Field-level encryption** (salary amounts and similar): future work, not built.
- **Secrets:** `SECRET_KEY` and settings come from environment variables (`backend/.env.example` lists them, no secrets); a secrets manager is future work.
- **Security headers, rate limiting, account lockout, multi-factor authentication, password reset, session list:** future work, not built (see `ordinis-security.md` for the status of each control).

## 7.3 Security Threat Analysis

| Threat | Mitigation |
|---|---|
| Cross-tenant access by changing an id | Querysets filtered by company; another company's object returns 404. Tested for every object route against the demo company (`core/test_api_matrix.py`) |
| A request with no login, or a new view that forgot its permission | Closed-by-default policy; the matrix test checks every route for 401 |
| Calling an endpoint directly without the Permission | `PermissionRequiredMixin` on the server; the matrix test checks 403 for every protected action and that the exact Permission gets past |
| Privilege escalation through client-controlled fields | `company`, `employee`, `assigned_by`, status of a leave request and similar are always set by the server |
| A suspended company still working | Login refused; `IsCompanyActive` blocks tokens issued earlier |
| A request approved by its own requester | The approval engine refuses it, even if the requester holds the step's Role |
| Platform operator misusing client data | No default access; Break-Glass needs a reason, company approval, a time limit, is read-only, excludes salary data, and every read is logged in `ImpersonationLog` |
| Tampering with the audit trail | `AuditLog` refuses update and delete in the model and the queryset, has no write endpoint, stores no field values, and a company can read only its own rows (404 for another company's). The other logs (`ImpersonationLog`, `PlatformActionLog`, `ApprovalAction`, `TaskProgressLog`) also have no edit or delete endpoint. A hash chain and database triggers are future work |
| Duplicate or replayed sensitive operations | `generate_payslip` is idempotent (service check plus database unique constraint) |

# 8. Performance Design

## 8.1 Performance Requirements

Per SRS NFR-5 and NFR-6: every list endpoint is paginated (page size 20). Tests assert that the number of database queries does not grow with the number of records for the Kanban board, the Action Inbox, the dashboard and payslip lists. No response time or concurrent-user target has been measured.

## 8.2 Scalability Strategy

- **Current:** one Django process and one database, enough for the course demonstration and a small pilot.
- **Future work (not built):** several stateless Django workers behind a load balancer (JWT keeps them stateless), Redis caching for dashboard queries, Celery workers for background jobs.

## 8.3 Capacity Planning

Not modelled. The plan employee limit (`SubscriptionPlan.max_employees`) is enforced when an Employee is created. The demo company has exactly 10 employees, so on the Basic plan it is full and shows the limit.

# 9. Error Handling & Logging

## 9.1 Error Handling Strategy

- `core/exceptions.py` (`OrdinisException` and the exception handler) turns every API error into the standard envelope with a `code`, a readable `message` and `field_errors`.
- Service functions raise typed errors for business rules (`LeaveError`, `PayslipError`, `ApprovalError`, a `ValueError` for an invalid task move); the handler turns them into a clear message, for example the remaining leave days.
- No retry mechanism exists because the system makes no external calls.

## 9.2 Logging Strategy

- **Audit logging:** `audit_log` writes one row for every create, update and delete made through the API (also leave decisions, payslips, approvals and Break-Glass reads), a Failed row for a refused write, and a Warning row for a delete or an export. The row names the actor, company, module, record, changed field names and IP address. Actions outside a request (a script, a test) are not logged; the demo-data loader logs as "System (demo data)". A logging error is written to the server log and never blocks the action. `AuditLoggingMixin` on the ViewSets is now a no-op kept for compatibility.
- **Server logs:** Django's default console logging; no log aggregation or error monitoring tool is configured.

# 10. Deployment Design

## 10.1 Deployment Strategy

No CI/CD pipeline exists. The workflow is manual: `python regression.py backend`, then `python regression.py selenium` (browser tests, needs Chrome and both servers), `npm run lint` and `npm run build`, then `git commit` and `git push` to the team repository. Both test commands exit non-zero on a failure (see `TESTING.md`). A GitHub Actions pipeline is future work.

## 10.2 Environment Configuration

| Environment | Purpose | Configuration |
|---|---|---|
| Dev | Local development | `config/settings/development.py`; `DEBUG=True`; SQLite; `runserver` and `npm run dev` |
| QA/Staging | Not provisioned | Future |
| Prod | Not provisioned | `config/settings/production.py` is a template (environment secrets, PostgreSQL); it has not been run |

## 10.3 Rollback Strategy

Git revert only. Migrations have been regenerated from scratch in development when conflicts occurred, so a reversible migration plan is a **known gap** to close before any deployment with real data.

# 11. Design Constraints

- **Technology:** Django + DRF (backend) and React (frontend) per the course project; no other framework was evaluated.
- **Timeline:** five two-week sprints (stories ST-101 to ST-137); a feature freeze after the first demo rehearsal (ST-133).
- **Regulatory:** none imposed for the course; data-privacy practice (tenant isolation, permission-gated financial data, Break-Glass access) is self-imposed in anticipation of commercial use.
- **Budget:** free-tier tools only (SQLite, local servers); no paid infrastructure.

# 12. Assumptions & Dependencies

- **Assumptions:** Each company has at least one CEO account for initial setup; users have basic computer literacy; a single-language (English) UI is acceptable for the current release; PostgreSQL will behave equivalently to SQLite for the schema as designed (not yet verified by an actual PostgreSQL migration test).
- **External system dependencies:** None currently (no payment gateway, no third-party API is called by the running system).
- **Third-party libraries:** Django, Django REST Framework, `djangorestframework-simplejwt`, React, Vite, Tailwind CSS — all open-source, no paid licenses required.

# 13. Traceability Matrix

Each requirement's **status (Done, Partly, Not built) and the story that delivered it** are in SRS Section 7.2, read from the code. This table links a requirement group to the component that implements it.

| Requirement | Component | Remarks |
|---|---|---|
| FR-1 to FR-4 (registration, login, who am I) | `accounts` | Atomic company and CEO creation; suspended company refused at login |
| FR-5 to FR-9 (organization, hierarchy) | `organization` | `reports_to` self-FK and recursive `services.py` functions |
| FR-10 to FR-13 (RBAC) | `rbac`, `core` permission classes | Designation and Role kept separate; FR-13 is Partly |
| FR-14 to FR-16 (approval chain, actions, delegation) | `approvals` | `GenericForeignKey`-based instance; finish handlers |
| FR-17 to FR-19 (tasks) | `tasks` | Kanban moves and progress entries; Projects, comments, attachments are future work |
| FR-20 to FR-23 (attendance, leave) | `attendance` | Leave goes through the Approval Chain (ST-129); the monthly calendar (`month_calendar`) is ST-137; Holiday Calendar is future work |
| FR-24 to FR-28 (payroll) | `payroll` | Expense and Reimbursement are future work |
| FR-29, FR-30 (notifications, inbox) | `notifications` | Task assignment and approval notices; Action Inbox |
| FR-31 (audit log) | `audit_log` | Signals plus middleware; CSV export; view_audit_log Permission |
| FR-32 (analytics) | `analytics` | Overview and daily Company Health Snapshot; Permission `view_analytics` |
| FR-33 (plan employee limit) | `billing` | Limit checked in the Employee serializer; Billing page; invoices |
| FR-34 to FR-36 (Break-Glass) | `platform_admin` | Request, approve/deny/revoke, expiry, access log |
| NFR-1 to NFR-4 (security) | `core`, `accounts`, `rbac` | Section 7 |
| NFR-5, NFR-6 (performance) | `core.pagination.OrdinisPagination` | Applied to every list |
| NFR-7 to NFR-9 (usability) | frontend design system and `dashboard` | Section 6.1 |
| NFR-10, NFR-11 (reliability) | `payroll.services`, `tasks.services`, `attendance.leave_services` | Section 5.2 |
| NFR-12, NFR-13 (maintainability) | Layered architecture, data model | Section 3.1 |
| NFR-14 (versioned API) | `config/urls.py` | Everything under `/api/v1/` |
| NFR-15 (attributable audit trail) | `audit_log`, `platform_admin` logs | Section 7.3 |

# 14. Appendices

## Appendix A — Glossary

See Section 1.3 of this document and Section 1.3 of the SRS (the same glossary).

## Appendix B — Diagrams

- Section 2.3 — System Context Diagram
- Section 3.2 — Architectural Layer Diagram
- Section 5.2 — Leave Approval Flow and Break-Glass Flow
- `ordinis-ER-diagram.md` — ER diagram of the delivered system (generated)
- `ordinis-full-ER-diagram.md` — the full commercial vision (future work)

## Appendix C — Supporting Documents

- `Ordinis_SRS.md` — Software Requirements Specification (companion), with the Done/Partly/Not built table
- `ordinis-project-structure.md` — as-built folders and files (generated)
- `ordinis-security.md` — security checklist with the status of each control
- `ordinis-error-handling.md` — error and edge-case reference with the status of each case
- `ordinis-frontend-design-system.md`, `ordinis-dashboard-design.md` — design references with what is built
- `TESTING.md` — how to run the backend and browser tests, and the demo logins
