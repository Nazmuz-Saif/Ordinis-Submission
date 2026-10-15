import random
from datetime import datetime, time, timedelta

from approvals.models import ApprovalAction, ApprovalInstance
from approvals.services import decide
from .leave_models import LeaveRequest, LeaveType
from .leave_services import apply_leave, cancel_leave
from .models import Attendance

ORDER = 50

LEAVE_TYPES = [('Annual Leave', 20), ('Sick Leave', 10), ('Casual Leave', 7)]

# who, leave type, first day and last day (days from today), reason, how far it got.
LEAVES = [
    ('dev2', 'Sick Leave', -6, -5, 'Fever, doctor advised two days of rest', 'approved'),
    ('employee', 'Sick Leave', -12, -10, 'Migraine and rest at home', 'approved'),
    ('employee', 'Annual Leave', 10, 12, 'Family wedding in Sylhet', 'pending'),
    ('designer', 'Casual Leave', 20, 20, 'Passport office appointment', 'waiting_for_hr'),
    ('sales1', 'Annual Leave', 5, 7, "Trip to Cox's Bazar", 'rejected'),
    ('employee', 'Casual Leave', 30, 30, 'Visa interview in the city', 'cancelled'),
]
REJECTION_COMMENT = 'Month-end sales closing. Please move this to next month.'
WEEKEND = (4, 5)   # Friday and Saturday


def _decide(instance, actor, decision, comment=''):
    decide(instance.id, actor, decision, comment)


def _leave_requests(ctx):
    types = {}
    for name, days in LEAVE_TYPES:
        types[name], created = LeaveType.objects.get_or_create(
            company=ctx.company, name=name, defaults={'days_allowed_per_year': days},
        )
        ctx.note('leave types', created)

    for who, type_name, first, last, reason, outcome in LEAVES:
        employee = ctx.emp(who)
        if LeaveRequest.objects.filter(employee=employee, reason=reason).exists():
            continue
        leave = apply_leave(
            employee, types[type_name], ctx.today + timedelta(days=first), ctx.today + timedelta(days=last), reason,
        )
        ctx.note('leave requests', True)
        instance = ApprovalInstance.objects.get(object_id=leave.id)
        manager, hr = ctx.emp('manager'), ctx.emp('hr')
        if outcome == 'cancelled':
            cancel_leave(leave)
        elif outcome == 'rejected':
            _decide(instance, manager, ApprovalAction.DECISION_REJECTED, REJECTION_COMMENT)
        elif outcome in ('waiting_for_hr', 'approved'):
            _decide(instance, manager, ApprovalAction.DECISION_APPROVED, 'Fine with me.')
            if outcome == 'approved':
                _decide(instance, hr, ApprovalAction.DECISION_APPROVED)


def _attendance(ctx):
    on_leave = {}
    for leave in LeaveRequest.objects.filter(company=ctx.company, status=LeaveRequest.STATUS_APPROVED):
        on_leave.setdefault(leave.employee_id, []).append((leave.start_date, leave.end_date))

    now_local = datetime.now(ctx.zone)
    days = [ctx.today - timedelta(days=n) for n in range(30, -1, -1)]
    for day in days:
        if day.weekday() in WEEKEND:
            continue
        for key, employee in ctx.employees.items():
            if any(start <= day <= end for start, end in on_leave.get(employee.id, [])):
                continue
            rng = random.Random(f'{employee.id}-{day}')
            if day == ctx.today:
                # Today: most people are in; the Employee and the Manager have NOT checked in yet, so the demo can do it live.
                if key in ('employee', 'manager') or now_local.hour < 10:
                    continue
                check_out = None
            else:
                if rng.random() < 0.07:   # absent: no record at all
                    continue
                check_out = time(17 + rng.randint(0, 1), rng.choice([0, 15, 30, 45]))
            check_in = time(8 + (1 if rng.random() < 0.8 else 0), rng.randint(0, 40) if rng.random() < 0.8 else rng.randint(41, 59))
            _, created = Attendance.objects.get_or_create(
                employee=employee, date=day,
                defaults={
                    'company': ctx.company,
                    'check_in': datetime.combine(day, check_in, tzinfo=ctx.zone),
                    'check_out': datetime.combine(day, check_out, tzinfo=ctx.zone) if check_out else None,
                },
            )
            ctx.note('attendance records', created)


def seed(ctx):
    _leave_requests(ctx)   # first: days of approved leave are not working days
    _attendance(ctx)
