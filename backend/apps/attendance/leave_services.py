"""
Leave rules. The balance is never stored: it is computed from the Leave Type and the requests, so
changing a type's days or cancelling a request is always reflected.

  remaining = days allowed per year - days of Pending and Approved requests in that calendar year
  A request that crosses New Year is split: each year's days must fit that year's balance.
"""
from datetime import date, timedelta

from django.db import transaction

from approvals.models import ApprovalChain, ApprovalInstance, ApprovalStep
from approvals.services import ApprovalError, cancel_approval, start_approval
from core.exceptions import OrdinisException
from organization.models import Employee
from rbac.models import EmployeeRole, Role
from rbac.services import CEO_ROLE_NAME
from .leave_models import LeaveRequest, LeaveType
from .services import local_today

LEAVE_MODULE = 'leave'
DEFAULT_CHAIN_NAME = 'Leave Approval (default)'


class LeaveError(OrdinisException):
    code = 'LEAVE_ERROR'
    message = 'The leave request could not be saved.'
    status_code = 400


def _plural(n):
    return f'{n} day' if n == 1 else f'{n} days'


def days_between(start, end):
    return (end - start).days + 1


def days_in_year(start, end, year):
    """How many days of start..end fall inside the calendar year."""
    lo, hi = max(start, date(year, 1, 1)), min(end, date(year, 12, 31))
    return max(0, (hi - lo).days + 1)


def used_days(employee, leave_type, year, statuses=LeaveRequest.COUNTED):
    requests = LeaveRequest.objects.filter(
        employee=employee, leave_type=leave_type, status__in=statuses,
        start_date__lte=date(year, 12, 31), end_date__gte=date(year, 1, 1),
    )
    return sum(days_in_year(r.start_date, r.end_date, year) for r in requests)


def balance_for(employee, year=None):
    """For each leave type of the company: allowed, approved, pending and remaining days in `year`."""
    if year is None:
        year = local_today(employee.company)[0].year
    result = []
    for leave_type in LeaveType.objects.filter(company_id=employee.company_id).order_by('name'):
        approved = used_days(employee, leave_type, year, [LeaveRequest.STATUS_APPROVED])
        pending = used_days(employee, leave_type, year, [LeaveRequest.STATUS_PENDING])
        result.append({
            'leave_type': leave_type.id, 'name': leave_type.name, 'year': year,
            'allowed': leave_type.days_allowed_per_year, 'approved': approved, 'pending': pending,
            'remaining': leave_type.days_allowed_per_year - approved - pending,
        })
    return result


# ---------------------------------------------------------------------------
# Which Approval Chain decides a leave request
# ---------------------------------------------------------------------------

def _step_without_approver(chain, applicant):
    """The first step nobody except the applicant can decide (no active holder of its role), or None."""
    for step in chain.steps.select_related('approver_role').order_by('step_order'):
        holders = EmployeeRole.objects.filter(
            role_id=step.approver_role_id, employee__user__is_active=True,
        ).exclude(employee_id=applicant.id)
        if not holders.exists():
            return step
    return None


def _default_chain(company):
    """
    The CEO fallback: one step, decided by the company's CEO role. It is created the first time it
    is needed and stays a normal chain, so the company can see and change it on the Approval Chains page.
    """
    role = (
        Role.objects.filter(company=company, is_system_default=True, name=CEO_ROLE_NAME).first()
        or Role.objects.filter(company=company, is_system_default=True).order_by('created_at').first()
    )
    if role is None:
        return None
    chain, _ = ApprovalChain.objects.get_or_create(
        company=company, name=DEFAULT_CHAIN_NAME, defaults={'applies_to_module': LEAVE_MODULE},
    )
    if not chain.steps.exists():
        ApprovalStep.objects.create(approval_chain=chain, step_order=1, approver_role=role)
    return chain


def leave_chain_for(employee):
    """
    The company's own leave chain (first by name) when every step has someone other than the applicant
    who can decide it. Otherwise the CEO fallback. Raises LeaveError when not even the CEO can decide.
    """
    own = (
        ApprovalChain.objects.filter(company_id=employee.company_id, applies_to_module=LEAVE_MODULE, steps__isnull=False)
        .exclude(name=DEFAULT_CHAIN_NAME).distinct().order_by('name', 'id').first()
    )
    if own and _step_without_approver(own, employee) is None:
        return own
    fallback = _default_chain(employee.company)
    if fallback and _step_without_approver(fallback, employee) is None:
        return fallback
    raise LeaveError(
        'No one can approve your leave right now. Ask an administrator to set up a leave approval chain.',
        code='LEAVE_NO_APPROVER',
    )


def on_approval_finished(instance):
    """Called by the approval engine when a request is approved or rejected: the leave follows the decision."""
    leave = LeaveRequest.objects.select_for_update().filter(pk=instance.object_id).first()
    if leave is None or leave.status != LeaveRequest.STATUS_PENDING:
        return
    approved = instance.status == ApprovalInstance.STATUS_APPROVED
    leave.status = LeaveRequest.STATUS_APPROVED if approved else LeaveRequest.STATUS_REJECTED
    leave.save(update_fields=['status', 'updated_at'])  # a rejected leave stops counting: the days are back


@transaction.atomic
def apply_leave(employee, leave_type, start_date, end_date, reason):
    """
    Create a Pending leave request, or refuse with a clear message:
    reversed dates, no reason, overlap with own leave, or more days than the balance of any year it touches.
    """
    if end_date < start_date:
        raise LeaveError('The end date cannot be before the start date.', code='LEAVE_END_BEFORE_START')
    reason = (reason or '').strip()
    if not reason:
        raise LeaveError('Give a reason for the leave.', code='LEAVE_REASON_REQUIRED')
    if leave_type.company_id != employee.company_id:
        raise LeaveError('Unknown leave type.', code='LEAVE_UNKNOWN_TYPE')

    # Two requests from one person at the same moment must not both pass the checks below.
    Employee.objects.select_for_update().get(pk=employee.pk)

    clash = LeaveRequest.objects.filter(
        employee=employee, status__in=LeaveRequest.COUNTED, start_date__lte=end_date, end_date__gte=start_date,
    ).first()
    if clash:
        raise LeaveError(
            f'You already have leave from {clash.start_date} to {clash.end_date} that overlaps these dates.',
            code='LEAVE_OVERLAP',
        )

    for year in range(start_date.year, end_date.year + 1):
        needed = days_in_year(start_date, end_date, year)
        remaining = leave_type.days_allowed_per_year - used_days(employee, leave_type, year)
        if needed > remaining:
            raise LeaveError(
                f'You asked for {_plural(needed)} of {leave_type.name}, but your remaining balance for {year} is {_plural(max(remaining, 0))}.',
                code='LEAVE_INSUFFICIENT_BALANCE',
            )

    chain = leave_chain_for(employee)   # raises LEAVE_NO_APPROVER before anything is saved
    leave = LeaveRequest.objects.create(
        company_id=employee.company_id, employee=employee, leave_type=leave_type,
        start_date=start_date, end_date=end_date, days=days_between(start_date, end_date), reason=reason,
    )
    try:
        start_approval(leave, chain, employee)
    except ApprovalError as exc:
        raise LeaveError(str(exc), code='LEAVE_NO_APPROVER')
    return leave


@transaction.atomic
def cancel_leave(leave_request):
    """The employee withdraws a request that is still Pending. The days go back to the balance."""
    leave_request = LeaveRequest.objects.select_for_update().get(pk=leave_request.pk)
    if leave_request.status != LeaveRequest.STATUS_PENDING:
        raise LeaveError('Only a pending request can be cancelled.', code='LEAVE_NOT_PENDING')
    leave_request.status = LeaveRequest.STATUS_CANCELLED
    leave_request.save(update_fields=['status', 'updated_at'])
    cancel_approval(leave_request)   # approvers no longer see it
    return leave_request
