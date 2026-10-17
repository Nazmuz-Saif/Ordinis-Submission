# ST-132 — What the documents said, and what the system really has

Written when the documents were synced to the delivered system (end of Sprint 5). "Old" is the version before ST-132. The code is the truth; where the code cannot be checked by a test, the document says so.

## Totals

| Item | Old documents | Delivered system |
|---|---|---|
| Django apps | 14 | 12 (no `audit_log`, `analytics`, `billing`) |
| Models in the SDS data dictionary | 36 | 26, generated from the code |
| API rows in the SDS | 37, of which 14 pointed at endpoints that do not exist | 141 endpoint methods on 91 routes, generated from the code |
| Requirements | 36 FR and 15 NFR, all written as if delivered | 51 requirements: 39 Done, 7 Partly, 5 Not built (SRS 7.2, read from the code) |
| Problems a script found by comparing the text to the code | 24 (14 endpoints, 10 class or field names) | 0 (`python manage.py check_docs`) |

## Difference list

| Document | Old statement | Reality | Now |
|---|---|---|---|
| SRS 1.2, 2.2 | Audit Log, Analytics, Billing limits, Payroll Expense and Reimbursement, Projects described as built | Not built (ST-134, ST-135, ST-136 pending; Expense, Reimbursement, Projects, Holiday Calendar not in the five sprints) | Marked future work |
| SRS 5 | ER diagram covered Project, TaskComment, TaskAttachment, HolidayCalendar, Expense, Reimbursement, AuditLog, CompanyHealthSnapshot, Billing | None of them exists | Points to the generated as-built ER diagram |
| SRS 7 | Traceability had Source and Acceptance only | No delivery status | 7.2 table with Done, Partly, Not built per requirement, read from the code |
| SDS 1.2, 2.2, 3.1, 3.2 | "Stage 1-7", 14 apps | Sprints 1 to 5, 12 apps | Corrected |
| SDS 3.3 | Django "latest stable", Celery, Redis, CI/CD "Stage 6" | Django 6.1, DRF 3.18; Selenium added; the rest not built | Corrected |
| SDS 4.2, 4.3 | Hand-written ER and data dictionary of 36 entities | 26 models; 11 listed entities do not exist (`AuditLog`, `CompanyHealthSnapshot`, `Expense`, `HolidayCalendar`, `Invoice`, `Project`, `Reimbursement`, `Subscription`, `SubscriptionPlan`, `TaskAttachment`, `TaskComment`) and 1 is a model the table never listed (`PlatformActionLog`) | Section generated from the models |
| SDS 5 | 14 components; `RolePermission` described as a model | 12 apps (plus `dashboard`); the link is a Many-to-many field | Rewritten; leave approval and Break-Glass flows redrawn |
| SDS 6.1 | Target look "pending implementation pass" | Implemented for most screens | Lists screens built and not built |
| SDS 6.3 | 37 endpoints, 14 of which do not exist (`approvals/actions`, `tasks/projects`, `tasks/progress-logs`, `payroll/expenses`, `audit-log/logs`, `analytics/snapshots`, `billing/...`, `platform-admin/tickets`, `.../access-requests`, `.../impersonation-logs`, `notifications/notifications/...`) | 141 methods on 91 routes | Section generated from the URL configuration |
| SDS 7 | Audit log "append-only by construction"; `IsCompanyActive` on every view | `AuditLog` does not exist. Some views had **no permission class at all** (open to anyone, a 500 error instead of 401): fixed in ST-131 | Closed-by-default policy documented; audit log marked future work |
| SDS 8, 9 | Pagination "must", `AuditLoggingMixin` as the logging system | Pagination built; the mixin is in place but writes nothing until `audit_log` exists | Corrected |
| SDS 10 | Manual PowerShell checks | Two regression commands | `python regression.py backend`, `selenium` |
| Project structure | Stage 1-7 tree with 14 apps and many "planned" files | 12 apps; a different frontend tree | Generated from the real folders |
| Security checklist | A target list with no status | Many controls not built (MFA, lockout, reset, headers, rate limit, encryption, audit log) | Status table: 13 Done, 1 Partly, 16 Not built, 2 not applicable |
| Error handling | A target list with no status | Several scenarios not handled (concurrent task edit, role delete with holders, team reassign prompt) | Status table |
| Design system | Names `SidebarGroup`, `NotificationDropdown`, `KanbanColumn`, `KanbanCard` | They are `Sidebar`, `NotificationBell`, `KanbanPage` | Corrected; status table of screens |
| Dashboard design | Dashboards for CTO, GM, AGM, Department Head; profile settings panel | One endpoint; sections by Permission; no profile settings panel | Status table |
| Final idea, Roadmap | Read as the delivered scope | They are vision | Banner added |
| ER (full) | Looked like the system | Commercial vision | Banner added; new as-built `ordinis-ER-diagram.md` |

## Not fixed on purpose

- The Appendix B interview analysis in the SRS is history and was not changed.
- `ordinis-final-idea.md` and `ordinis-roadmap.md` stay as vision documents; only a banner was added.
- When ST-134, ST-135 and ST-136 are merged, run `python manage.py generate_docs`. The data dictionary, API table, ER diagram, structure and the Done/Partly/Not built table update by themselves. A hand-written sentence that says "future work (ST-13x)" must then be edited: search the documents for `ST-134`, `ST-135`, `ST-136`.
