# Software Requirements Specification (SRS)

**Project Title:** Ordinis — A Dynamic, Multi-Tenant Workflow & Chain-of-Command Configuration Platform

### Team Info

| SL | Student ID | Student Name | Role |
|---|---|---|---|
| 1 |  | Saif |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

| Document Version | Date of Submission |
|---|---|
| V1.0 |  |

## Contents

- [Document History](#document-history)
- **1. Introduction**
  - [1.1 Purpose](#11-purpose)
  - [1.2 Scope](#12-scope)
  - [1.3 Definitions, Acronyms, and Abbreviations](#13-definitions-acronyms-and-abbreviations)
  - [1.4 References](#14-references)
  - [1.5 Overview](#15-overview)
- **2. Overall Description**
  - [2.1 Product Perspective](#21-product-perspective)
  - [2.2 Product Functions](#22-product-functions)
  - [2.3 User Classes and Characteristics](#23-user-classes-and-characteristics)
  - [2.4 Operating Environment](#24-operating-environment)
  - [2.5 Design and Implementation Constraints](#25-design-and-implementation-constraints)
  - [2.6 Assumptions and Dependencies](#26-assumptions-and-dependencies)
- **3. Specific Requirements**
  - [3.1 Functional Requirements](#31-functional-requirements)
    - [3.1.1 Authentication & Company Onboarding](#311-authentication--company-onboarding)
    - [3.1.2 Organization & Hierarchy Management](#312-organization--hierarchy-management)
    - [3.1.3 Role-Based Access Control (RBAC)](#313-role-based-access-control-rbac)
    - [3.1.4 Approval Workflow Engine](#314-approval-workflow-engine)
    - [3.1.5 Task & Project Management](#315-task--project-management)
    - [3.1.6 Attendance & Leave Management](#316-attendance--leave-management)
    - [3.1.7 Payroll Management](#317-payroll-management)
    - [3.1.8 Notifications & Action Inbox](#318-notifications--action-inbox)
    - [3.1.9 Audit Log & Analytics](#319-audit-log--analytics)
    - [3.1.10 Billing & Subscription](#3110-billing--subscription)
    - [3.1.11 Platform Administration (Break-Glass Access)](#3111-platform-administration-break-glass-access)
  - [3.2 Non-Functional Requirements](#32-non-functional-requirements)
    - [3.2.1 Security Requirements](#321-security-requirements)
    - [3.2.2 Performance Requirements](#322-performance-requirements)
    - [3.2.3 Usability Requirements](#323-usability-requirements)
    - [3.2.4 Reliability Requirements](#324-reliability-requirements)
    - [3.2.5 Maintainability Requirements](#325-maintainability-requirements)
    - [3.2.6 Portability Requirements](#326-portability-requirements)
    - [3.2.7 Auditability/Compliance Requirements](#327-auditabilitycompliance-requirements)
- **4. External Interface Requirements**
  - [4.1 User Interfaces](#41-user-interfaces)
  - [4.2 Hardware Interfaces](#42-hardware-interfaces)
  - [4.3 Software Interfaces](#43-software-interfaces)
- [**5. System Models**](#5-system-models)
- [**6. Other Requirements**](#6-other-requirements)
- [**7. Requirements Traceability**](#7-requirements-traceability)
- **Appendix**
  - [Appendix A: Requirement Elicitation/Discovery Process](#appendix-a-requirement-elicitationdiscovery-process)
  - [Appendix B: Survey/Questionnaire Responses and Statistics](#appendix-b-surveyquestionnaire-responses-and-statistics)

---

## Document History

| Version | Date | Authors | Change Log | Approved By |
|---|---|---|---|---|
| V1.0 |  | Saif | Initial version — full FR/NFR set, interview elicitation, and analysis |  |

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for **Ordinis**, a configurable, multi-tenant "Organization Operating System" (OrgOS). It is intended for use by developers, the course evaluator, and — beyond the course context — future adopting companies, to define precisely what the system must do (functional requirements) and how well it must do it (non-functional requirements). It also documents the requirement-elicitation process (stakeholder interviews) that these requirements were derived from.

### 1.2 Scope

Ordinis is a web-based, multi-tenant SaaS platform that lets any client company configure its own organizational hierarchy, roles/permissions, and approval workflows, instead of being forced into one fixed structure. Within the current build (and this SRS's scope), the system covers:

- Company onboarding and authentication (JWT-based)
- Dynamic organization builder (Departments, Designations, self-referencing Employee hierarchy)
- Permission-based Role-Based Access Control (RBAC), kept strictly separate from Designation
- A data-driven Approval Workflow engine (Approval Chains/Steps/Instances/Actions, Delegation), also used for leave requests
- Task management (with a Kanban board) and daily progress tracking; Projects are future work
- Attendance and Leave management
- Payroll (Salary Structure and Payslip are built; Expense and Reimbursement are future work) — an optional module per company
- Notifications and a personalized "Action Inbox"
- System-wide, append-only Audit Logging (future work, ST-135)
- Basic company-health Analytics (future work, ST-134)
- Subscription/Billing enforcement (employee-count plan limits) (future work, ST-136)
- Platform-level Super Admin operations under a privacy-respecting "Break-Glass" access pattern

**What is delivered (read this with Section 7.2).** Section 7.2 lists every requirement as Done, Partly or Not built, read from the code. These parts of the list above are *not built* and are future work: Projects (Tasks stand alone), Task comments and attachment links, the Holiday Calendar, Expense and Reimbursement, the append-only Audit Log, the Analytics page and Company Health Snapshot, and the plan employee-limit enforcement (Billing). The last four are Sprint 5 stories (ST-134, ST-135, ST-136) and move to Done in Section 7.2 by themselves when their code is merged.

Out of scope for this SRS (documented separately as future roadmap, not built or required in the current course-project scope): Layer-3 extension modules such as Meetings, Internal Ticketing, Asset Management, Document Management, Knowledge Base, Performance Reviews, Surveys, Visitor Management, Dynamic Form Builder, mobile app, multi-language switcher, third-party/ERP data import-export, and public API/webhooks. These recurred as stakeholder wishes during elicitation (see Appendix B analysis) but are consciously deferred so the current release stays focused and buildable within the course timeline.

### 1.3 Definitions, Acronyms, and Abbreviations

- **OrgOS** – Organization Operating System
- **SaaS** – Software as a Service
- **RBAC** – Role-Based Access Control
- **Designation** – An employee's job title/label (e.g., "Senior Developer"); carries no access rights by itself
- **Role** – A named bundle of Permissions (e.g., "Approver", "Finance Manager") assignable to any Employee regardless of Designation
- **Permission** – A single, named capability codename (e.g., `approve_leave`, `view_finance`) checked by the backend before allowing an action
- **Tenant** – A single client Company using the shared Ordinis platform; all of a tenant's data is isolated from other tenants
- **Reports To** – The self-referencing field on Employee that defines who an employee's manager is, forming the organizational hierarchy tree
- **Approval Chain** – A company-defined, ordered sequence of Approval Steps that a request (e.g., leave, expense) must pass through
- **Break-Glass Access** – A time-limited, company-approved, fully logged exception process that lets a Platform Admin access a specific company's data only when explicitly granted
- **JWT** – JSON Web Token, used for stateless API authentication
- **API** – Application Programming Interface
- **CEO** – Chief Executive Officer (used generically for "company owner/top authority" in this document)
- **GM/AGM** – General Manager / Assistant General Manager
- **HR** – Human Resources
- **FR / NFR** – Functional Requirement / Non-Functional Requirement

### 1.4 References

- IEEE Std 830-1998, Recommended Practice for Software Requirements Specifications
- Ordinis Project Proposal (`project-proposal.md`)
- Ordinis Final Idea Summary (`ordinis-final-idea.md`)
- Ordinis Master Build Prompt (`ordinis-master-prompt.md`)
- Ordinis Full ER Diagram (`ordinis-full-ER-diagram.md`)
- Ordinis Security Reference (`ordinis-security.md`)
- Ordinis Error Handling Reference (`ordinis-error-handling.md`)
- Ordinis Frontend Design System (`ordinis-frontend-design-system.md`)
- Ordinis Dashboard Design Reference (`ordinis-dashboard-design.md`)
- Ordinis Stakeholder Interview Questionnaire and Digitized Responses (`Ordinis_Interviews_Digitized.md`)
- Ordinis Project Structure — as built (`ordinis-project-structure.md`, generated from the code)
- Ordinis ER Diagram — as built (`ordinis-ER-diagram.md`, generated from the code); the full commercial vision is `ordinis-full-ER-diagram.md` (future)
- Ordinis Sprint Planning workbook (`Ordinis_Sprint_Planning_Final.xlsx`) — stories ST-101 to ST-137

### 1.5 Overview

Section 2 describes Ordinis at a high level — its perspective, functions, user classes, environment, and constraints. Section 3 gives the detailed, itemized functional and non-functional requirements, each with a priority. Section 4 covers external interfaces. Section 5 references the system's data/process models. Section 6 lists other requirements. Section 7 provides a requirements traceability matrix linking requirements back to their stakeholder source. The Appendices document the interview-based elicitation process in full, including the questionnaire, all responses, demographics, and the resulting analysis.

---

## 2. Overall Description

### 2.1 Product Perspective

Ordinis is a new, standalone multi-tenant SaaS web application. It is not a plug-in to any existing HR/ERP system. Each client company ("tenant") signs up independently; a single deployment of Ordinis serves many tenants simultaneously, with strict data isolation between them (every record is scoped by `company_id`). The system exposes a versioned REST API (Django REST Framework) consumed by a React single-page-application dashboard. There is no legacy system Ordinis integrates with in the current scope — it is designed to **replace** the ad-hoc mix of Excel, WhatsApp, and verbal communication that stakeholder interviews confirmed is the current norm.

### 2.2 Product Functions

At a high level, Ordinis lets a company:

1. Register itself and its first CEO account, then build its own Department/Designation/Employee structure
2. Define its own Roles as bundles of Permissions, independent of job titles
3. Configure its own multi-step Approval Chains for things like leave and expense requests
4. Assign, track, and review Tasks/Projects with daily progress logs
5. Record Attendance (check-in/check-out) and manage Leave requests against configurable Leave Types
6. Optionally run Payroll — salary structures, payslip generation, expense/reimbursement
7. See a personalized "Action Inbox" of only what needs that user's attention
8. Rely on a full, append-only Audit Log of sensitive actions
9. See basic company health analytics (attendance rate, task completion rate)
10. Operate under a subscription plan with an enforced employee-count limit
11. (Platform level) Let the Ordinis operator provide support without ever having silent default access to a client's operational data

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Skill Expected |
|---|---|---|
| Super Admin (Platform Owner) | Operates Ordinis itself — manages tenant companies, subscriptions, support tickets; has **no default access** to any company's operational data | Technical/administrative |
| CEO / Company Owner | Full control within their own company: structure, roles, approvals, billing, company-wide visibility | Low–medium; expects a simple, guided UI |
| GM / AGM | Executes CEO's plans across departments; monitors and assigns at department-head level | Low–medium |
| Department Head / Team Lead | Manages their own team's tasks, attendance, and first-level leave approval | Low |
| HR (functional role) | Employee lifecycle, leave approval step, document/holiday management — independent of hierarchy position | Low–medium |
| Accountant / Finance (optional functional role) | Payroll, expense, and salary data only — explicitly walled off from task/HR data | Low–medium |
| Employee | Own tasks, attendance, leave application, payslip viewing | Low; must be usable with minimal/no training |

### 2.4 Operating Environment

- **Client:** Modern web browsers (Chrome, Firefox, Edge) on desktop; the UI must also remain usable on common mobile browser widths
- **Backend Server:** Python 3 + Django + Django REST Framework, served via WSGI (Gunicorn/uWSGI in production)
- **Database:** SQLite for development; PostgreSQL is the target for production
- **Frontend:** React (Vite), Tailwind CSS
- **Authentication:** Stateless JWT (access + refresh tokens)
- **OS:** Platform-independent server (Linux target for production; developed on Windows)

### 2.5 Design and Implementation Constraints

- Every data model must be scoped by `company` (tenant) — no exceptions, enforced at the API permission layer since Django middleware cannot see the JWT-resolved user
- Designation must never be used as an access-control check in code; only Permission codenames may gate an action
- Organizational hierarchy, roles, permissions, and approval chains must be stored as data, never as hardcoded conditional logic, so a new company's structure requires zero code changes
- Business logic must live in `services.py` modules, kept separate from thin HTTP view logic
- All API responses must use a consistent envelope: `{success, data, message}` on success or `{success, error: {code, message, field_errors}}` on failure
- Course timeline constraint: development follows a fixed staged build order (Foundation → Core Engine → Business Modules → Frontend), and Layer-3 "nice to have" modules identified during interviews are explicitly deferred, not built now

### 2.6 Assumptions and Dependencies

- Each client company has at least one designated CEO/owner account to perform initial setup
- Users have basic computer/smartphone literacy and stable internet access during use
- The company's own device/network provides internet connectivity; Ordinis does not need to function fully offline in the current scope
- Payroll module usage is optional per company and assumes the company is comfortable digitizing salary data
- The current release targets a single language (English UI strings), with Bangla/English switching explicitly deferred as future work

---

## 3. Specific Requirements

### 3.1 Functional Requirements

> Requirements are tagged **High**, **Medium**, or **Low** priority. IDs are grouped by module for traceability with Section 7. This section states what the system *must* do. Section 7.2 states which of these are Done, Partly or Not built in the delivered system.

#### 3.1.1 Authentication & Company Onboarding

- **FR-1** (High) — The system shall allow a new company to self-register in a single atomic operation that creates the Company, its default CompanySettings, a CEO Designation, and the first CEO User/Employee account.
- **FR-2** (High) — The system shall authenticate users via email and password and issue a JWT access token and refresh token upon success.
- **FR-3** (High) — The system shall reject login attempts for users belonging to a suspended company, returning a clear, specific error rather than a generic failure.
- **FR-4** (Medium) — The system shall provide an endpoint that returns the authenticated user's identity, company, designation, and current permission list, for the frontend to render the correct UI.

#### 3.1.2 Organization & Hierarchy Management

- **FR-5** (High) — The system shall allow authorized users to create, view, update, and delete Departments within their own company.
- **FR-6** (High) — The system shall allow authorized users to create, view, update, and delete Designations within their own company.
- **FR-7** (High) — The system shall allow authorized users to create and manage Employee records, including assigning each Employee's Department, Designation, and manager (`reports_to`).
- **FR-8** (High) — The system shall support an arbitrary-depth self-referencing hierarchy (via `reports_to`) so that flat, 3-level, or 4+ level company structures are all supported without any code change.
- **FR-9** (Medium) — The system shall be able to recursively resolve, for any Employee, the full list of subordinates (descendants) and the full chain of managers (ancestors).

#### 3.1.3 Role-Based Access Control (RBAC)

- **FR-10** (High) — The system shall allow authorized users to create company-specific Roles, each defined as a named bundle of one or more Permissions.
- **FR-11** (High) — The system shall allow one or more Roles to be assigned to any Employee, independent of that Employee's Designation.
- **FR-12** (High) — The system shall check a specific Permission codename before allowing any protected create/update/delete action, rather than relying on Designation name or login status alone.
- **FR-13** (High) — The system shall restrict visibility of an Employee's operational data (e.g., tasks, attendance) to that Employee, their manager chain, and any user holding an explicit company-wide viewing permission.

#### 3.1.4 Approval Workflow Engine

- **FR-14** (Medium) — The system shall allow a company to define an Approval Chain made up of one or more ordered Approval Steps, each tied to an approver Role.
- **FR-15** (Medium) — The system shall record every Approval Action (approve/reject, with actor and optional comment) against a specific Approval Instance.
- **FR-16** (Medium) — The system shall allow an Employee to delegate their approval authority to another Employee for a specified date range (Delegation Rule).

#### 3.1.5 Task & Project Management

- **FR-17** (High) — The system shall allow authorized users to create Projects and assign Tasks to Employees, each Task carrying a status, priority, deadline, and progress percentage.
- **FR-18** (High) — The system shall allow an assignee to submit a Task for review only via valid status transitions, rejecting invalid transitions (e.g., "Completed" directly back to "Not Started").
- **FR-19** (Medium) — The system shall allow Employees to record daily progress logs (text update, progress percentage, optional external reference link) plus comments and attachment links against a Task, without requiring code/file uploads.

#### 3.1.6 Attendance & Leave Management

- **FR-20** (High) — The system shall allow Employees to check in and check out once per calendar day, timestamped using the company's local time zone.
- **FR-21** (High) — The system shall allow Employees to apply for Leave against a company-defined Leave Type, and shall validate the request against the Employee's remaining leave balance before accepting it.
- **FR-22** (High) — The system shall allow an authorized approver to approve or reject a pending Leave Request.
- **FR-23** (Medium) — The system shall allow authorized users to define company-specific Leave Types and Holiday Calendar entries.

#### 3.1.7 Payroll Management

- **FR-24** (High) — The system shall allow authorized users to define a Salary Structure per Employee, consisting of a base salary and a set of allowances.
- **FR-25** (High) — The system shall generate a Payslip for a given Employee, month, and year, computing gross amount, deductions, and net amount, and shall prevent generating a duplicate Payslip for the same Employee/month/year.
- **FR-26** (Medium) — The system shall allow Employees to submit Expense/reimbursement claims and allow an authorized approver to approve or reject each claim.
- **FR-27** (Medium) — The system shall record an approved Reimbursement's paid amount and payment date against its originating Expense.
- **FR-28** (High) — The system shall restrict all Salary Structure, Payslip, and Expense data visibility to users holding a finance-specific Permission, independent of their position in the reporting hierarchy.

#### 3.1.8 Notifications & Action Inbox

- **FR-29** (Medium) — The system shall generate an in-app Notification for relevant events (e.g., task assignment, leave decision, approval request).
- **FR-30** (Medium) — The system shall provide an aggregated "Action Inbox" view per user, combining pending task reviews, pending approvals, and unread notifications relevant to that user into a single list.

#### 3.1.9 Audit Log & Analytics

- **FR-31** (High) — The system shall automatically record every create, update, and delete action performed through the API — capturing actor, action, affected model, and timestamp — into an append-only Audit Log that cannot be edited or deleted by any user, including Super Admin.
- **FR-32** (Low) — The system shall be able to compute and store a periodic Company Health Snapshot, derived from the company's attendance rate and task completion rate.

#### 3.1.10 Billing & Subscription

- **FR-33** (Medium) — The system shall enforce an employee-count limit on each company based on its active Subscription Plan, blocking the creation of a new Employee once the plan's limit is reached.

#### 3.1.11 Platform Administration (Break-Glass Access)

- **FR-34** (Medium) — The system shall require a Platform Admin to submit a Support Access Request, stating a reason, before being granted any access to a specific company's operational data.
- **FR-35** (Medium) — The system shall require the target company (its CEO or an authorized approver) to explicitly approve a Support Access Request before any access is granted, and shall only grant access for a fixed, time-limited window that expires automatically.
- **FR-36** (Medium) — The system shall record every Break-Glass access session (start time, end time, target employee/data, and reason) in an Impersonation Log that the company can review afterward.

---

### 3.2 Non-Functional Requirements

#### 3.2.1 Security Requirements

- **NFR-1** (High) — All user passwords shall be stored using a one-way, industry-standard hash (Django's PBKDF2); plaintext passwords shall never be stored or logged.
- **NFR-2** (High) — Every database query shall be scoped by the requesting user's company (tenant isolation); an attempt to access another tenant's resource by ID shall return HTTP 404, not 403, so that the resource's mere existence is not leaked.
- **NFR-3** (High) — Authentication shall use short-lived JWT access tokens with refresh-token rotation, minimizing the exposure window if a token is stolen.
- **NFR-4** (High) — Every protected API endpoint shall verify a specific Permission codename server-side; the frontend hiding a button is a UX convenience only and shall never be the sole enforcement mechanism.

#### 3.2.2 Performance Requirements

- **NFR-5** (Medium) — All list-returning API endpoints shall be paginated so response times remain acceptable as a company's data volume grows.
- **NFR-6** (Low) — Under normal single-company demonstration load, standard pages (login, dashboards) shall load and respond within a few seconds.

#### 3.2.3 Usability Requirements

- **NFR-7** (Medium) — The user interface shall apply one consistent, minimalist visual design (fixed color palette, typography scale, and subtle 150–300ms animation) across every module, so a non-technical company owner is not confused by inconsistent screens.
- **NFR-8** (Medium) — All user-facing error messages shall be specific and actionable (e.g., naming the missing permission or the exceeded leave balance) rather than a generic "something went wrong."
- **NFR-9** (Medium) — Core day-to-day actions (checking in, applying for leave, updating a task) shall be reachable within minimal clicks from an Employee's dashboard, requiring little to no training, consistent with the strong stakeholder preference recorded during elicitation (see Appendix B).

#### 3.2.4 Reliability Requirements

- **NFR-10** (High) — Payslip generation shall be idempotent: attempting to generate a second Payslip for the same Employee, month, and year shall be rejected rather than creating a duplicate record.
- **NFR-11** (Medium) — Leave balance checks and Task status-transition checks shall be enforced consistently at the service layer so that no client-side bypass can create an inconsistent state.

#### 3.2.5 Maintainability Requirements

- **NFR-12** (Medium) — Business logic shall be implemented in dedicated service-layer modules, separate from HTTP view/controller code, so logic can be tested and modified independently of the API layer.
- **NFR-13** (High) — Organizational hierarchy, roles/permissions, and approval workflows shall be represented as configurable data rather than hardcoded application logic, so onboarding a new company with a different structure requires no source-code change.

#### 3.2.6 Portability Requirements

- **NFR-14** (Low) — The backend shall expose a versioned REST API (`/api/v1/...`) decoupled from any specific frontend, so the same API can serve the current web dashboard and a future mobile client without modification.

#### 3.2.7 Auditability/Compliance Requirements

- **NFR-15** (High) — Every approve, reject, edit, and delete action on a sensitive record shall be attributable to a specific actor and timestamp in the Audit Log, directly satisfying the near-universal stakeholder request (see Appendix B) to see a history/audit trail after important actions.

---

## 4. External Interface Requirements

### 4.1 User Interfaces

- A web-based, responsive dashboard (React + Tailwind CSS), with role-specific dashboard layouts (CEO, Manager, HR/Accountant, Employee, Super Admin)
- A dedicated Login page and a guided Company Setup Wizard for first-time onboarding
- Sidebar navigation + top navbar layout, consistent across all authenticated screens
- Forms for all create/edit operations (Departments, Designations, Employees, Tasks, Leave Requests, Payroll records, Roles, Approval Chains)
- A personalized "Action Inbox" surfaced prominently for every logged-in user

### 4.2 Hardware Interfaces

- No dedicated/proprietary hardware is required. The system runs on standard server hardware (or cloud VM) and is accessed from standard client devices (desktop/laptop/smartphone) with a display and network connection.

### 4.3 Software Interfaces

- **Database interface:** Django ORM to SQLite (development) / PostgreSQL (production)
- **API interface:** Django REST Framework, JSON over HTTPS, versioned at `/api/v1/`
- **Authentication interface:** `djangorestframework-simplejwt` for JWT issuance/validation
- **Browser interface:** Standard HTTP/HTTPS, consumed by the React SPA via `fetch`/axios-style HTTP client

---

## 5. System Models

The following models, maintained as separate project artifacts, define Ordinis's structure and are referenced here rather than duplicated in full:

- **Entity-Relationship Diagram** — the delivered system's ER diagram is generated from the code and is in `ordinis-ER-diagram.md`; it covers Company, Organization (Department, Designation, Employee with self-referencing `reports_to`), RBAC (Permission, Role, EmployeeRole), the Approval engine (ApprovalChain, ApprovalStep, ApprovalInstance, ApprovalAction, DelegationRule), Tasks (Task, TaskProgressLog), Attendance and Leave (Attendance, LeaveType, LeaveRequest), Payroll (SalaryStructure, Payslip), Notification, and Platform Admin (SupportTicket, SupportAccessRequest, ImpersonationLog, PlatformActionLog). The commercial vision, with entities that are not built (Project, TaskComment, TaskAttachment, HolidayCalendar, Expense, Reimbursement, AuditLog, CompanyHealthSnapshot, SubscriptionPlan, Subscription, Invoice and the Layer 3 modules), is `ordinis-full-ER-diagram.md` and is future work.
- **Use Case Model** — implicit in Section 3.1, organized by module; each Functional Requirement corresponds to one or more user-triggered use cases (e.g., "Employee applies for Leave", "Department Head approves a Task submission").
- **Data Flow** — Requests flow: Browser (React SPA) → REST API (`/api/v1/...`, JWT-authenticated) → DRF View → Service layer → Django ORM → Database, where relevant also producing a Notification. (A write also producing an Audit Log entry is future work, ST-135.)
- **State Model (Task)** — Task status follows a constrained state machine (Not Started → In Progress → Submitted → Completed, or Rejected back to Not Started), enforced in `tasks/services.py`, matching FR-18.
- **State Model (Approval Instance)** — An Approval Instance advances step-by-step through its Approval Chain as each Approval Action is recorded, matching FR-14/FR-15.

---

## 6. Other Requirements

- **Legal/Compliance:** As a future (post-course) commercial product, Ordinis will require a Terms of Service and Privacy Policy consistent with its data-handling practices, particularly around the Break-Glass access pattern (FR-34–36) and payroll/salary data (FR-28).
- **Localization:** The current release ships English-only UI strings, written in a way that anticipates a future Bangla/English switcher (translation-key-ready), but the switcher itself is out of current scope.
- **Data Retention:** A clear policy on how long a company's data is retained after subscription cancellation is required before commercial launch; not required for the course-project demonstration.
- **Academic Constraint:** This SRS and the underlying system are being developed to satisfy a Software Engineering course deliverable in parallel with (and feeding into) a longer-term commercial roadmap; Layer-3/Layer-4/Layer-5 features described in the project's roadmap document are explicitly out of scope for this SRS.

---

## 7. Requirements Traceability

### 7.1 Source and acceptance criteria


| Req ID | Requirement (short) | Source (Stakeholder/Interview) | Priority | Acceptance Criteria |
|---|---|---|---|---|
| FR-1 | Company self-registration | CEO Interviews Q7 (guided setup preference) | High | New company + CEO account created in one call; JWT returned |
| FR-2 | JWT login | CEO/GM/HR/Accountant/Employee interviews (all — implicit baseline) | High | Valid credentials return access+refresh token; invalid return generic error |
| FR-3 | Block suspended-company login | Derived from Billing/SaaS model (project-proposal.md) | High | Suspended company's user login attempt returns specific error, no token |
| FR-4 | "Who am I" endpoint | Frontend/RBAC UI requirement | Medium | Returns user, company, designation, permissions |
| FR-5–FR-6 | Department/Designation CRUD | CEO Interview Q4 (hierarchy varies by company) | High | CRUD works, scoped to own company only |
| FR-7–FR-8 | Employee + reports_to hierarchy | CEO Interview Q4, Q5 (structure & access levels vary) | High | Arbitrary-depth hierarchy created without code change |
| FR-9 | Recursive subordinate/manager resolution | Dept Head Interview Q2 (visibility into team) | Medium | Correct recursive result for a multi-level test tree |
| FR-10–FR-11 | Role/Permission bundle & assignment | CEO Interview Q6; HR Interview Q8 (separated responsibilities) | High | Role created with permission set; assignable to any Employee |
| FR-12–FR-13 | Permission-check enforcement & hierarchy-scoped visibility | Dept Head Interview Q2; Accountant Interview Q4 (confidentiality) | High | Action blocked without permission; data scoped correctly |
| FR-14–FR-15 | Approval Chain/Step/Action | CEO Interview Q9; HR Interview Q4 (HR's step in approval) | Medium | Multi-step chain executes in order; actions logged |
| FR-16 | Delegation Rule | GM/AGM Interview Q4; Dept Head Interview Q7 (delegate while absent) | Medium | Delegate can act within date range only |
| FR-17–FR-18 | Task/Project CRUD + status transition validation | Dept Head Interview Q1–Q2; CEO Interview Q8 | High | Invalid transition rejected; valid one succeeds |
| FR-19 | Daily progress log | Dept Head Interview Q3 (multi-day monitoring) | Medium | Log entries stored with date, text, %, optional link |
| FR-20 | Check-in/out | Employee Interview Q1 | High | Duplicate same-day check-in blocked |
| FR-21–FR-22 | Leave apply + balance check + approval | Employee Interview Q3, Q7; Dept Head Interview Q4 | High | Over-balance request blocked; approver can approve/reject |
| FR-23 | Leave Type/Holiday config | HR Interview Q2 | Medium | Company-specific types/holidays configurable |
| FR-24–FR-25 | Salary Structure + Payslip generation | Accountant Interview Q1–Q2; CEO Interview Q11 | High | Duplicate payslip for same month blocked |
| FR-26–FR-27 | Expense + Reimbursement | Accountant Interview Q5 | Medium | Claim approved/rejected; reimbursement recorded |
| FR-28 | Finance-only data visibility | Accountant Interview Q4 (confidentiality) | High | Non-finance user cannot view salary data |
| FR-29–FR-30 | Notifications + Action Inbox | Employee Interview Q6, Q7; CEO Interview Q19 | Medium | Relevant event triggers notification; inbox aggregates correctly |
| FR-31 | Append-only Audit Log | Near-universal across all 6 groups (audit-trail question) | High | Log entry created on every write; no edit/delete endpoint exists |
| FR-32 | Company Health Snapshot | CEO Interview Q10 | Low | Snapshot value reflects real attendance+task data |
| FR-33 | Plan employee-limit enforcement | Business model (project-proposal.md, Section 6) | Medium | Employee creation blocked at plan limit |
| FR-34–FR-36 | Break-Glass Support Access | CEO Interview Q13, Q20 (security concerns) | Medium | Access requires approval, expires on time, is logged |
| NFR-1–NFR-4 | Security (hashing, tenant isolation, JWT, permission checks) | All interviews, Q13/Q17/Q20-type security questions | High | Verified via manual cross-tenant/permission test cases |
| NFR-5–NFR-6 | Pagination, response time | Non-functional/course constraint | Medium/Low | Manual timing check under demo load |
| NFR-7–NFR-9 | Usability, minimal training | All interviews' "training-free" question | Medium | New user completes core task without written help |
| NFR-10–NFR-11 | Idempotency, consistent validation | Accountant Interview Q1 (duplicate payroll risk) | High/Medium | Duplicate/invalid operation rejected consistently |
| NFR-12–NFR-13 | Service-layer separation, data-driven config | Design principle (master-prompt.md) | Medium/High | Code review confirms no hardcoded role/hierarchy logic |
| NFR-14 | Versioned, portable API | Future mobile-app roadmap | Low | `/api/v1/` prefix present on all endpoints |
| NFR-15 | Attributable audit trail | Near-universal audit-trail question | High | Every sensitive action traceable to actor+timestamp |

---

### 7.2 Delivery status of every requirement

Each requirement is Done, Partly or Not built. **The status is read from the code** (models, endpoints, classes) by `python manage.py generate_docs`; nobody edits it by hand. A requirement that cannot be checked from code carries a fixed status and a reason in its Note. "Delivered by" names the sprint stories (ST-nnn).

<!-- BEGIN GENERATED:traceability -->
| Req ID | Requirement | Priority | Status | Delivered by | Note |
|---|---|---|---|---|---|
| FR-1 | Company self-registration (company, settings, CEO) in one step | High | **Done** | ST-101 |  |
| FR-2 | Email and password login with JWT access and refresh tokens | High | **Done** | ST-102 |  |
| FR-3 | Login refused for a suspended company, with a clear error | High | **Done** | ST-103 |  |
| FR-4 | "Who am I" endpoint (user, company, designation, permissions) | Medium | **Done** | ST-102 |  |
| FR-5 | Departments: create, view, update, delete | High | **Done** | ST-104 |  |
| FR-6 | Designations: create, view, update, delete | High | **Done** | ST-105 |  |
| FR-7 | Employees with department, designation and manager (reports_to) | High | **Done** | ST-106 |  |
| FR-8 | Arbitrary-depth reporting hierarchy through reports_to | High | **Done** | ST-106 |  |
| FR-9 | Full list of subordinates and managers resolved recursively | Medium | **Done** | ST-107 |  |
| FR-10 | Company Roles as named bundles of Permissions | High | **Done** | ST-108 |  |
| FR-11 | Roles assigned to any Employee, independent of Designation | High | **Done** | ST-109 |  |
| FR-12 | A specific Permission codename is checked before every protected action | High | **Done** | ST-110, ST-111 |  |
| FR-13 | Operational data visible only to the employee, the manager chain and company-wide permission holders | High | **Partly** | ST-107, ST-111, ST-116 | Tasks, leave requests and payslips are limited to the owner, assignee, approver or a permission holder. A manager cannot yet list a team member's attendance. |
| FR-14 | Approval Chain of ordered steps, each tied to a Role | Medium | **Done** | ST-112 |  |
| FR-15 | Every approve or reject recorded with actor and comment | Medium | **Done** | ST-113 |  |
| FR-16 | Delegation of approval authority for a date range | Medium | **Done** | ST-117 |  |
| FR-17 | Projects and Tasks with status, priority, deadline | High | **Partly** | ST-116, ST-125 | Not in the code yet: model Project |
| FR-18 | Task status changes only along valid transitions | High | **Done** | ST-116, ST-125 |  |
| FR-19 | Daily progress log, comments and attachment links on a Task | Medium | **Partly** | ST-125 | Not in the code yet: model TaskComment, model TaskAttachment |
| FR-20 | One check-in and one check-out per day in the company time zone | High | **Done** | ST-119 |  |
| FR-21 | Leave application validated against the remaining balance | High | **Done** | ST-128 |  |
| FR-22 | An approver approves or rejects a Pending leave request | High | **Done** | ST-129 |  |
| FR-23 | Leave Types and a Holiday Calendar per company | Medium | **Partly** | ST-128 | Not in the code yet: model HolidayCalendar |
| FR-24 | Salary Structure per Employee (base salary and allowances) | High | **Done** | ST-118, ST-120 |  |
| FR-25 | Payslip per Employee and month, no duplicates | High | **Done** | ST-127 |  |
| FR-26 | Expense claims approved or rejected | Medium | **Not built** | (not in the 5 sprints) | Not in the code yet: model Expense |
| FR-27 | Reimbursement recorded against an approved Expense | Medium | **Not built** | (not in the 5 sprints) | Not in the code yet: model Reimbursement |
| FR-28 | Salary and payslip data limited to the finance Permission | High | **Done** | ST-118, ST-120, ST-127 |  |
| FR-29 | In-app Notification for task assignment and approvals | Medium | **Done** | ST-126 |  |
| FR-30 | Action Inbox combining tasks, approvals and notifications | Medium | **Done** | ST-126 |  |
| FR-31 | Append-only Audit Log of every create, update and delete | High | **Not built** | ST-135 | Not in the code yet: model AuditLog |
| FR-32 | Company health analytics (attendance rate, task completion) | Low | **Not built** | ST-134 | Not in the code yet: endpoint /api/v1/analytics/ or /api/v1/dashboard/analytics/ |
| FR-33 | Employee limit enforced by the subscription plan | Medium | **Not built** | ST-136 | Not in the code yet: model SubscriptionPlan, model Subscription, code can_add_employee |
| FR-34 | Platform Admin must send a Support Access Request with a reason | Medium | **Done** | ST-123 |  |
| FR-35 | The company approves; access is time-limited and expires by itself | Medium | **Done** | ST-123 |  |
| FR-36 | Every Break-Glass access recorded where the company can read it | Medium | **Done** | ST-123, ST-124 |  |
| NFR-1 | Passwords stored with a one-way hash (PBKDF2) | High | **Done** | ST-101, ST-102 | Django default hasher. A fast hasher is used only while the tests run (settings/base.py). |
| NFR-2 | Tenant isolation: another company's object is a 404, not a 403 | High | **Done** | ST-111, ST-131 |  |
| NFR-3 | Short-lived access token, rotating refresh token, blacklist on logout | High | **Done** | ST-102 |  |
| NFR-4 | Every protected endpoint checks its Permission on the server; secure by default | High | **Done** | ST-110, ST-111, ST-131 |  |
| NFR-5 | All list endpoints are paginated | Medium | **Done** | ST-121 |  |
| NFR-6 | Standard pages answer within a few seconds under demo load | Low | **Partly** | ST-121 | No timing was measured. Tests assert the query count does not grow with the number of records on the board, inbox, dashboard and payslip lists. |
| NFR-7 | One consistent minimalist design across every module | Medium | **Done** | ST-114, ST-115 |  |
| NFR-8 | Specific, actionable error messages | Medium | **Done** | ST-111, ST-128 | Business rules return a named code and a readable message (for example the remaining leave days). |
| NFR-9 | Core actions within a few clicks, little or no training | Medium | **Partly** | ST-122 | Role dashboards and an Action Inbox exist. No usability test with real users was run. |
| NFR-10 | Payslip generation is idempotent | High | **Done** | ST-127 |  |
| NFR-11 | Leave balance and Task transitions enforced in the service layer | Medium | **Done** | ST-116, ST-128 |  |
| NFR-12 | Business logic in service modules, not in views | Medium | **Done** | ST-111 | services.py in organization, tasks, attendance, payroll, approvals, notifications, platform_admin, dashboard. |
| NFR-13 | Hierarchy, roles and approval chains are data, not code | High | **Done** | ST-106, ST-108, ST-112 |  |
| NFR-14 | Versioned REST API under /api/v1/ | Low | **Done** | ST-102 |  |
| NFR-15 | Every sensitive action attributable to an actor and a time | High | **Partly** | ST-123, ST-135 | Not in the code yet: model AuditLog |

*51 requirements: 39 Done, 7 Partly, 5 Not built. Status is read from the code by `python manage.py generate_docs`.*
<!-- END GENERATED:traceability -->

---

## Appendix A: Requirement Elicitation/Discovery Process

### A.1 Method

Requirements were elicited primarily through **structured one-on-one interviews**, using a fixed multiple-choice-plus-"Other" questionnaire designed separately for each of six stakeholder groups (CEO, GM/AGM, Department Head/Team Lead, HR Executive, Accountant/Finance, Employee). This method was chosen because:

- The target users (small/growing company owners and staff in Bangladesh) are more comfortable talking through their current pain points than filling out an open-ended written survey
- A fixed-option format with an "Other" escape hatch balances **speed of data collection** (quick to tick) against **completeness** (free text still possible when no option fits)
- Interviewing rather than only surveying let the interviewer probe follow-ups on ambiguous or interesting answers (e.g., asking a CEO to elaborate on payroll expectations in free text)

### A.2 Questionnaire Design

Six separate interview sheets were prepared (20 questions for CEO — the most central stakeholder — down to 8 questions for GM/AGM), each opening with a demographics block (Company/Organization, Interviewee, Interviewer, Date) before the substantive questions. Several questions (audit trail necessity, notification channel preference, security/data-leak concerns, training-friendliness) were deliberately repeated **across all six sheets in a standardized form**, specifically so that answers could be compared side-by-side across roles during analysis (see A.4 and Appendix B.3).

### A.3 Sample and Coverage

A total of **10 interviews** were conducted and digitized, covering all 6 required stakeholder groups (meeting the rubric's ≥2-per-group target for every group except AGM/GM and Accountant, which reached the minimum via combined coverage — see the demographic table in Appendix B.1 for the exact breakdown):

| Stakeholder Group | Interviews Conducted |
|---|---|
| CEO | 2 |
| GM / AGM | 2 |
| Department Head / Team Lead | 2 |
| HR Executive | 2 |
| Accountant / Finance | 1 |
| Employee | 1 |

Interviewees were drawn from real or realistic small-to-mid-size Bangladeshi companies (a software/IT company, a trading/retail business, a small manufacturing unit, and others), giving the requirement set grounding in actual current practice (Excel, WhatsApp, biometric devices, third-party tools like ClickUp/Jira) rather than assumption alone.

### A.4 From Interview to Requirement

Each interview response was reviewed for: (a) restating an already-planned Ordinis feature (validating it), (b) surfacing a **new** requirement not yet in the design, or (c) requesting something explicitly **out of current course-project scope** (flagged as future roadmap, per Section 1.2). The resulting Functional and Non-Functional Requirements in Section 3, and their Section 7 traceability links, are the direct output of this triage process. The full analysis with cross-role patterns is presented in Appendix B.3.

---

## Appendix B: Survey/Questionnaire Responses and Statistics

### B.1 Demographics

**Interviewer demographics** (constant across all 10 interviews): Saif, CSE student, University of Asia Pacific, conducting elicitation for the Ordinis Software Engineering course project.

**Interviewee demographics:**

| # | Stakeholder Role | Company/Organization | Interview Date |
|---|---|---|---|
| 1 | CEO | Software/IT company | — |
| 2 | CEO | Trading/retail business | — |
| 3 | GM/AGM | Software/IT company | — |
| 4 | GM/AGM | Manufacturing unit | — |
| 5 | Department Head/Team Lead | Software/IT company | — |
| 6 | Department Head/Team Lead | Trading/retail business | — |
| 7 | HR Executive | Manufacturing unit | — |
| 8 | HR Executive | Software/IT company | — |
| 9 | Accountant/Finance | Trading/retail business | — |
| 10 | Employee | Software/IT company | — |

*(Company names and exact dates are as recorded in `Ordinis_Interviews_Digitized.md`; omitted/generalized here for confidentiality where the source sheet left them blank.)*

### B.2 Full Questionnaire and Responses

The complete question set (20 CEO / 8 GM-AGM / 11 Dept Head / 17 HR / 16 Accountant / 12 Employee questions) and every recorded answer are preserved in full in the companion file **`Ordinis_Interviews_Digitized.md`**, submitted alongside this SRS. That file contains, per interview: the demographics block, every question, the selected option(s), and any free-text "Other" answers exactly as recorded — it is treated as the raw data source for the summary and analysis below rather than being re-transcribed in full here to avoid duplication.

### B.3 Cross-Role Analysis and Key Insights

The following patterns emerged from comparing answers across the 10 interviews and directly shaped the requirements in Section 3:

**1. Current tooling is fragmented and manual, validating the core premise.**
Across CEO, Department Head, and Employee interviews, current task/attendance tracking relies on WhatsApp, verbal communication, Excel sheets, or at best a generic third-party tool (ClickUp, Jira) not designed for the company's specific hierarchy. This directly validates the need for Ordinis's own Task (FR-17–19) and Attendance/Leave (FR-20–23) modules rather than assuming the problem away.

**2. Hierarchy-based and permission-based access is a near-unanimous, strongly-felt requirement.**
Both CEOs, both Department Heads, and both HR interviewees independently confirmed that different employees need different access levels, and several explicitly separated "who can see what" from "what title someone holds" — directly confirming the Designation-vs-Role design decision (FR-10–13) rather than it being an academic exercise.

**3. Approval flow is rarely single-step and often role-dependent, not fixed.**
Responses varied between "direct manager only," "manager then HR," and "HR then CEO" for leave approval, and Department Heads explicitly wanted a way to hand off their approval authority when absent. This is exactly why Approval Chains are modeled as **configurable data** (FR-14) rather than a hardcoded two-step flow, and why Delegation (FR-16) was added as a first-class requirement rather than a nice-to-have.

**4. Financial data confidentiality is treated as strict and non-negotiable.**
The Accountant interview and CEO interviews consistently placed salary/financial visibility as "Accountant + CEO only" or "each employee sees only their own," explicitly separate from general HR or task visibility. This is the direct source of FR-28's requirement that finance data access be permission-gated independent of the reporting hierarchy — a stricter rule than the general hierarchy-visibility rule in FR-13.

**5. Audit trail / action history is the single most consistent request across every group.**
Every one of the six stakeholder sheets contains a version of "do you feel it's necessary to see the history/audit trail after approve/reject/edit actions," and every interviewee answered "yes" (for every action, or at least major ones). This directly motivated making FR-31 (audit log) and NFR-15 (attributable audit trail) **High** priority rather than a secondary feature.

**6. Security/data-leak concern is universal but generic — it validates NFRs rather than adding new FRs.**
Every interview included a security-concern question, and responses were consistently affirmative but rarely specified a concrete mechanism. This was interpreted as strong support for the Security NFRs already planned (tenant isolation, hashed passwords, permission checks — NFR-1–4) rather than grounds for new stakeholder-specific functional features.

**7. Training-friendliness is consistently demanded, reinforcing usability priority.**
Every non-CEO group was asked how much training would be acceptable, and the dominant answer across Department Head, HR, Accountant, and GM/AGM interviews was "should be simple/training-free" or "a little training is fine." This is the direct source of NFR-9 (minimal-click core actions, low learning curve).

**8. Several genuinely useful requests fall outside current scope and were consciously deferred, not ignored.**
A subset of requests recur but push into Layer-3/future territory already defined in the project's own roadmap document: WhatsApp/SMS notification channels (vs. the in-app/email channels actually built), full offline/low-connectivity usage, mobile-app-first usage patterns for some roles (e.g., accountants wanting mobile access "regularly"), import/export integration with existing tools (ClickUp, generic accounting software), and a Bangla/English language toggle. These are **not** written into Section 3 as current Functional Requirements — doing so would silently expand scope beyond what Stage 1–7 of the actual build covers — but are explicitly retained here as validated future-roadmap items with a real stakeholder source, to be picked up after the current core engine and business modules are stable.

**9. Data migration from existing systems is a recognized but secondary need.**
Several CEOs and the Accountant raised concern about bringing in old Excel/WhatsApp history or existing accounting-software data. Since no current FR covers data import, this is flagged here as a known gap for a future release rather than silently dropped.

### B.4 Summary of Requirement Yield

Of the 10 interviews, cross-referencing every question against the existing Ordinis design produced: **31 questions that directly validated an already-planned feature**, **9 that surfaced a refinement to a planned feature** (e.g., Delegation, finance-only visibility strictness), and **6 recurring themes redirected to the future-roadmap backlog** rather than expanding current scope. This triage is what keeps Section 3's 36 FRs and 15 NFRs grounded in real stakeholder evidence while staying inside the buildable, current-course scope defined in Section 1.2.
