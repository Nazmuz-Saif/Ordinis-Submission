"""
Break-Glass rules. Views stay thin; every rule lives here.

  request  -> pending
  pending  -> approved (CEO, with a time limit) | denied (CEO)
  approved -> revoked (CEO, any time) | over by itself when expires_at passes

A Platform Admin can read a company's data ONLY while one approved, unexpired
request of theirs exists for that company, and every read is written to the log.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from tenants.models import Company
from .exceptions import SupportAccessError, SupportAccessRequired
from .models import ImpersonationLog, SupportAccessRequest

DEFAULT_HOURS = 24
MAX_HOURS = 72


def _now():
    return timezone.now()


def effective_status(access_request):
    """The status users see. An approved request past its time limit reads as 'expired'."""
    if access_request.status == SupportAccessRequest.STATUS_APPROVED:
        if access_request.expires_at is None or access_request.expires_at <= _now():
            return 'expired'
    return access_request.status


def create_request(admin_user, company, reason):
    reason = (reason or '').strip()
    if not reason:
        raise SupportAccessError('Give a reason for the access request.', code='SUPPORT_REASON_REQUIRED')
    open_ones = SupportAccessRequest.objects.filter(
        company=company, requested_by=admin_user,
        status__in=[SupportAccessRequest.STATUS_PENDING, SupportAccessRequest.STATUS_APPROVED],
    )
    for existing in open_ones:
        if effective_status(existing) in ('pending', 'approved'):
            raise SupportAccessError(
                'You already have an open request for this company.', code='SUPPORT_REQUEST_ALREADY_OPEN',
            )
    return SupportAccessRequest.objects.create(company=company, requested_by=admin_user, reason=reason)


def _locked(access_request):
    return SupportAccessRequest.objects.select_for_update().get(pk=access_request.pk)


@transaction.atomic
def approve(access_request, employee, hours=None):
    access_request = _locked(access_request)
    if access_request.status != SupportAccessRequest.STATUS_PENDING:
        raise SupportAccessError('Only a pending request can be approved.', code='SUPPORT_NOT_PENDING')
    hours = DEFAULT_HOURS if hours in (None, '') else hours
    try:
        hours = int(hours)
    except (TypeError, ValueError):
        raise SupportAccessError('Hours must be a whole number.', code='SUPPORT_BAD_HOURS')
    if not 1 <= hours <= MAX_HOURS:
        raise SupportAccessError(f'Access can last 1 to {MAX_HOURS} hours.', code='SUPPORT_BAD_HOURS')
    now = _now()
    access_request.status = SupportAccessRequest.STATUS_APPROVED
    access_request.decided_by = employee
    access_request.decided_at = now
    access_request.expires_at = now + timedelta(hours=hours)
    access_request.save()
    return access_request


@transaction.atomic
def deny(access_request, employee):
    access_request = _locked(access_request)
    if access_request.status != SupportAccessRequest.STATUS_PENDING:
        raise SupportAccessError('Only a pending request can be denied.', code='SUPPORT_NOT_PENDING')
    access_request.status = SupportAccessRequest.STATUS_DENIED
    access_request.decided_by = employee
    access_request.decided_at = _now()
    access_request.save()
    return access_request


@transaction.atomic
def revoke(access_request, employee):
    access_request = _locked(access_request)
    if effective_status(access_request) != 'approved':
        raise SupportAccessError('Only access that is still running can be revoked.', code='SUPPORT_NOT_ACTIVE')
    now = _now()
    access_request.status = SupportAccessRequest.STATUS_REVOKED
    access_request.decided_by = employee
    access_request.decided_at = now
    access_request.expires_at = now
    access_request.save()
    return access_request


def require_active_grant(admin_user, company_id):
    """The one gate for reading company data. Returns the grant, or raises 403."""
    grant = (
        SupportAccessRequest.objects.filter(
            company_id=company_id, requested_by=admin_user,
            status=SupportAccessRequest.STATUS_APPROVED, expires_at__gt=_now(),
        ).order_by('-expires_at').first()
    )
    if grant is None or not Company.objects.filter(pk=company_id).exists():
        raise SupportAccessRequired()
    return grant


def log_access(grant, admin_user, method, endpoint, detail=''):
    return ImpersonationLog.objects.create(
        access_request=grant, actor=admin_user, method=method, endpoint=endpoint[:255], detail=detail[:255],
    )


# ---------- Admin panel (ST-124) ----------
from .models import PlatformActionLog, SupportTicket  # noqa: E402


NOTE_MIN = 10
NOTE_MAX = 255            # the length of PlatformActionLog.note
NOTE_MAX_TICKET = 500     # the length of SupportTicket.resolution_note


def clean_note(note, what='the note', minimum=NOTE_MIN, maximum=NOTE_MAX):
    """The trimmed note, or a clear 400 when it is missing, too short or too long."""
    note = (note or '').strip() if isinstance(note, str) or note is None else str(note).strip()
    if not note:
        raise SupportAccessError(f'Write {what} (at least {minimum} characters).', code='NOTE_REQUIRED', field_errors={'note': ['This field is required.']})
    if len(note) < minimum:
        raise SupportAccessError(
            f'{what[0].upper()}{what[1:]} is too short: write at least {minimum} characters.', code='NOTE_TOO_SHORT',
            field_errors={'note': [f'At least {minimum} characters.']},
        )
    if len(note) > maximum:
        raise SupportAccessError(
            f'{what[0].upper()}{what[1:]} is too long: {maximum} characters at most.', code='NOTE_TOO_LONG',
            field_errors={'note': [f'At most {maximum} characters.']},
        )
    return note


def _record(admin_user, company, action, note=''):
    return PlatformActionLog.objects.create(
        actor=admin_user, company=company, company_name=company.name, action=action, note=note[:255],
    )


def record_payment_action(admin_user, payment, action, note=''):
    """One PlatformActionLog row for a payment decision. The Audit Log rows come from the model signals."""
    return _record(admin_user, payment.company, action, f'{payment.transaction_id}: {note}')


@transaction.atomic
def set_company_active(admin_user, company, active, note=''):
    """Suspend or activate a company. A note of at least 10 characters is required: every action is explained.
    Repeating the same call changes nothing and logs nothing."""
    note = clean_note(note, 'the reason')
    if company.is_active == active:
        return company
    company.is_active = active
    company.save()
    _record(admin_user, company, 'activate' if active else 'suspend', note)
    return company


def create_ticket(employee, subject, description=''):
    subject = (subject or '').strip()
    if not subject:
        raise SupportAccessError('Give the ticket a subject.', code='TICKET_SUBJECT_REQUIRED')
    return SupportTicket.objects.create(
        company=employee.company, created_by=employee, subject=subject, description=(description or '').strip(),
    )


@transaction.atomic
def set_ticket_resolved(admin_user, ticket, resolved, note=''):
    """Resolving needs a resolution note of at least 10 characters (the company reads it); reopening needs none."""
    if resolved:
        note = clean_note(note, 'the resolution note', maximum=NOTE_MAX_TICKET)
    wanted = SupportTicket.STATUS_RESOLVED if resolved else SupportTicket.STATUS_OPEN
    if ticket.status == wanted:
        return ticket
    ticket.status = wanted
    ticket.resolved_at = _now() if resolved else None
    ticket.resolution_note = note if resolved else ''
    ticket.save()
    _record(admin_user, ticket.company, 'resolve_ticket' if resolved else 'reopen_ticket', f'{ticket.subject}: {note}' if resolved else ticket.subject)
    return ticket
