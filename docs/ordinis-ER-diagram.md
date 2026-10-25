# Ordinis — ER Diagram (as built)

This is the ER diagram of the **delivered system**. It is generated from the real foreign keys of the Django models by `python manage.py generate_docs`, so it cannot show an entity that does not exist, and a test fails if it drifts from the code. The field list of every model is in the data dictionary (SDS Section 4.3).

The **full commercial vision** (Project, TaskComment, TaskAttachment, HolidayCalendar, Expense, Reimbursement, AuditLog, CompanyHealthSnapshot, SubscriptionPlan, Subscription, Invoice, and the Layer 3 modules) is in `ordinis-full-ER-diagram.md`. That file is future work, not the delivered system.

<!-- BEGIN GENERATED:er-diagram -->
Built from the real foreign keys. `id`, timestamps and `is_deleted` are on every model and are not drawn. Links through `GenericForeignKey` (an approval or a notification pointing at any record) are not drawn.

```mermaid
erDiagram
  APPROVALCHAIN ||--o{ APPROVALINSTANCE : approval_chain
  APPROVALCHAIN ||--o{ APPROVALSTEP : approval_chain
  APPROVALINSTANCE ||--o{ APPROVALACTION : instance
  APPROVALSTEP |o--o{ APPROVALACTION : step
  COMPANY |o--o{ AUDITLOG : company
  COMPANY |o--o{ PLATFORMACTIONLOG : company
  COMPANY |o--o{ USER : company
  COMPANY ||--o{ APPROVALCHAIN : company
  COMPANY ||--o{ APPROVALINSTANCE : company
  COMPANY ||--o{ ATTENDANCE : company
  COMPANY ||--o{ COMPANYHEALTHSNAPSHOT : company
  COMPANY ||--o{ DELEGATIONRULE : company
  COMPANY ||--o{ DEPARTMENT : company
  COMPANY ||--o{ DESIGNATION : company
  COMPANY ||--o{ EMPLOYEE : company
  COMPANY ||--o{ EMPLOYEEROLE : company
  COMPANY ||--o{ INVOICE : company
  COMPANY ||--o{ LEAVEREQUEST : company
  COMPANY ||--o{ LEAVETYPE : company
  COMPANY ||--o{ NOTIFICATION : company
  COMPANY ||--o{ PAYMENTSUBMISSION : company
  COMPANY ||--o{ PAYSLIP : company
  COMPANY ||--o{ ROLE : company
  COMPANY ||--o{ SALARYSTRUCTURE : company
  COMPANY ||--o{ SUPPORTACCESSREQUEST : company
  COMPANY ||--o{ SUPPORTTICKET : company
  COMPANY ||--o{ TASK : company
  COMPANY ||--o| COMPANYSETTINGS : company
  COMPANY ||--o| SUBSCRIPTION : company
  DEPARTMENT |o--o{ EMPLOYEE : department
  DESIGNATION |o--o{ EMPLOYEE : designation
  EMPLOYEE |o--o{ DEPARTMENT : head
  EMPLOYEE |o--o{ EMPLOYEE : reports_to
  EMPLOYEE |o--o{ PAYMENTSUBMISSION : submitted_by
  EMPLOYEE |o--o{ PAYSLIP : generated_by
  EMPLOYEE |o--o{ SUPPORTACCESSREQUEST : decided_by
  EMPLOYEE |o--o{ SUPPORTTICKET : created_by
  EMPLOYEE |o--o{ TASK : assigned_by
  EMPLOYEE ||--o{ APPROVALACTION : actor
  EMPLOYEE ||--o{ APPROVALINSTANCE : requested_by
  EMPLOYEE ||--o{ ATTENDANCE : employee
  EMPLOYEE ||--o{ DELEGATIONRULE : delegate
  EMPLOYEE ||--o{ DELEGATIONRULE : delegator
  EMPLOYEE ||--o{ EMPLOYEEROLE : employee
  EMPLOYEE ||--o{ LEAVEREQUEST : employee
  EMPLOYEE ||--o{ NOTIFICATION : recipient
  EMPLOYEE ||--o{ PAYSLIP : employee
  EMPLOYEE ||--o{ TASK : assigned_to
  EMPLOYEE ||--o{ TASKPROGRESSLOG : employee
  EMPLOYEE ||--o| SALARYSTRUCTURE : employee
  INVOICE |o--o{ PAYMENTSUBMISSION : invoice
  LEAVETYPE ||--o{ LEAVEREQUEST : leave_type
  ROLE ||--o{ APPROVALSTEP : approver_role
  ROLE ||--o{ EMPLOYEEROLE : role
  ROLE }o--o{ PERMISSION : permissions
  SUBSCRIPTION ||--o{ INVOICE : subscription
  SUBSCRIPTIONPLAN |o--o{ SUBSCRIPTION : next_plan
  SUBSCRIPTIONPLAN ||--o{ PAYMENTSUBMISSION : plan
  SUBSCRIPTIONPLAN ||--o{ SUBSCRIPTION : plan
  SUPPORTACCESSREQUEST ||--o{ IMPERSONATIONLOG : access_request
  TASK ||--o{ TASKPROGRESSLOG : task
  USER |o--o{ AUDITLOG : actor
  USER |o--o{ PAYMENTSUBMISSION : reviewed_by
  USER ||--o{ IMPERSONATIONLOG : actor
  USER ||--o{ PLATFORMACTIONLOG : actor
  USER ||--o{ SUPPORTACCESSREQUEST : requested_by
  USER ||--o| EMPLOYEE : user
  USER {
    Char128 password
    DateTime last_login
    Boolean is_superuser
    fk company
    Char254 email
    Char150 full_name
    Boolean must_change_password
    Boolean is_active
    Boolean is_staff
    Boolean is_platform_admin
  }
  COMPANYHEALTHSNAPSHOT {
    fk company
    Date date
    PositiveInteger headcount
    Decimal4_1 attendance_rate
    Decimal4_1 task_completion_rate
    PositiveInteger open_tasks
    PositiveInteger overdue_tasks
    Decimal4_1 health_score
  }
  APPROVALACTION {
    fk instance
    fk step
    PositiveInteger step_order
    fk actor
    Char20 decision
    Text comment
  }
  APPROVALCHAIN {
    fk company
    Char100 name
    Char50 applies_to_module
  }
  APPROVALINSTANCE {
    fk company
    fk approval_chain
    fk content_type
    UUID object_id
    fk requested_by
    PositiveInteger current_step
    Char20 status
  }
  APPROVALSTEP {
    fk approval_chain
    PositiveInteger step_order
    fk approver_role
  }
  DELEGATIONRULE {
    fk company
    fk delegator
    fk delegate
    Date start_date
    Date end_date
    Char255 reason
  }
  ATTENDANCE {
    fk company
    fk employee
    Date date
    DateTime check_in
    DateTime check_out
  }
  LEAVEREQUEST {
    fk company
    fk employee
    fk leave_type
    Date start_date
    Date end_date
    PositiveSmallInteger days
    Char500 reason
    Char20 status
  }
  LEAVETYPE {
    fk company
    Char60 name
    PositiveSmallInteger days_allowed_per_year
  }
  AUDITLOG {
    fk company
    Char255 company_name
    fk actor
    Char254 actor_email
    Char20 action
    Char10 status
    Char50 module
    Char100 model_name
    Char64 object_id
    Char255 object_repr
    JSON changed_fields
    GenericIPAddress ip_address
  }
  INVOICE {
    fk company
    fk subscription
    Char40 number
    Char50 plan_name
    Date period_start
    Date period_end
    Decimal10_2 amount
    Char10 currency
    Char10 status
    Date issued_on
    Date due_on
    Date paid_on
    Char10 payment_method
    Char64 transaction_id
    Char10 kind
    PositiveSmallInteger months
  }
  PAYMENTSUBMISSION {
    fk company
    fk plan
    PositiveSmallInteger months
    Decimal10_2 amount
    Char10 currency
    Char10 method
    Char100 payer_name
    Char30 payer_number
    Char64 transaction_id
    Char10 kind
    Char10 status
    fk submitted_by
    fk reviewed_by
    DateTime reviewed_at
    Char500 review_note
    Date period_start
    Date period_end
    fk invoice
  }
  SUBSCRIPTION {
    fk company
    fk plan
    Char20 status
    Date started_on
    Date current_period_start
    Date current_period_end
    PositiveSmallInteger billing_months
    JSON reminders_sent
    fk next_plan
    Date next_plan_from
  }
  SUBSCRIPTIONPLAN {
    Char50 name
    PositiveInteger max_employees
    Decimal10_2 price_monthly
    Char10 currency
    Boolean is_active
  }
  NOTIFICATION {
    fk company
    fk recipient
    Char30 kind
    Char200 title
    Char500 message
    Char200 link
    Boolean is_read
    DateTime read_at
  }
  DEPARTMENT {
    fk company
    Char100 name
    fk head
  }
  DESIGNATION {
    fk company
    Char100 title
  }
  EMPLOYEE {
    fk user
    fk company
    fk department
    fk designation
    fk reports_to
    Char50 employee_code
    Char30 phone
    Char255 address
    Char100 emergency_contact_name
    Char30 emergency_contact_phone
    Date joined_on
  }
  PAYSLIP {
    fk company
    fk employee
    PositiveSmallInteger year
    PositiveSmallInteger month
    Decimal12_2 base_salary
    JSON allowances
    Decimal12_2 gross_amount
    Decimal12_2 deductions
    Char255 deduction_note
    Decimal12_2 net_amount
    fk generated_by
  }
  SALARYSTRUCTURE {
    fk company
    fk employee
    Decimal12_2 base_salary
    JSON allowances
  }
  IMPERSONATIONLOG {
    fk access_request
    fk actor
    Char10 method
    Char255 endpoint
    Char255 detail
  }
  PLATFORMACTIONLOG {
    fk actor
    fk company
    Char255 company_name
    Char40 action
    Char255 note
  }
  SUPPORTACCESSREQUEST {
    fk company
    fk requested_by
    Text reason
    Char20 status
    fk decided_by
    DateTime decided_at
    DateTime expires_at
  }
  SUPPORTTICKET {
    fk company
    fk created_by
    Char200 subject
    Text description
    Char20 status
    DateTime resolved_at
  }
  EMPLOYEEROLE {
    fk employee
    fk role
    fk company
  }
  PERMISSION {
    Char100 codename
    Char255 name
    Char50 module
    Char500 description
  }
  ROLE {
    fk company
    Char100 name
    Text description
    Boolean is_system_default
  }
  TASK {
    fk company
    Char200 title
    Text description
    fk assigned_to
    fk assigned_by
    Char10 priority
    Date deadline
    Char20 status
  }
  TASKPROGRESSLOG {
    fk task
    fk employee
    Date date
    Text update_text
    PositiveSmallInteger progress_percent
    Char500 blocker_text
    Char500 external_reference_url
  }
  COMPANY {
    Char255 name
    Slug subdomain
    Char200 logo
    Char100 industry
    Boolean is_active
  }
  COMPANYSETTINGS {
    fk company
    Char10 currency
    Char50 timezone
    Char10 fiscal_year_start
    Char10 default_language
  }
```
<!-- END GENERATED:er-diagram -->
