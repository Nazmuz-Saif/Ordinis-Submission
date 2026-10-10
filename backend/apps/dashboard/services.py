"""
Dashboard numbers. Every function returns plain dicts for ONE section of the dashboard.

Which sections a user gets depends only on their Permissions, never on their Designation:

    me       everyone                       own tasks, own attendance today, approvals waiting for them
    team     create_task                    company task numbers
    people   manage_employees               headcount, departments, attendance today
    finance  manage_finance                 payroll totals from Salary Structures
"""
from collections import Counter
from decimal import Decimal

from django.db.models import Avg, Count, Sum

from approvals.models import ApprovalInstance, ApprovalStep
from approvals.services import can_act, effective_role_ids
from attendance.models import Attendance
from attendance.services import local_today
from organization.models import Department, Employee
from payroll.models import SalaryStructure
from tasks.models import Task

TEAM_PERMISSION = 'create_task'
PEOPLE_PERMISSION = 'manage_employees'
FINANCE_PERMISSION = 'manage_finance'

STATUSES = [key for key, _ in Task.STATUS_CHOICES]
PRIORITIES = [key for key, _ in Task.PRIORITY_CHOICES]


def _by_status(queryset):
    counts = {row['status']: row['n'] for row in queryset.values('status').annotate(n=Count('id'))}
    return {status: counts.get(status, 0) for status in STATUSES}


def _overdue(queryset, today):
    return queryset.filter(deadline__lt=today).exclude(status=Task.STATUS_COMPLETED).count()


def _money(value):
    return float(Decimal(value or 0).quantize(Decimal('0.01')))


def me_section(employee, today):
    mine = Task.objects.filter(company=employee.company, assigned_to=employee)
    record = Attendance.objects.filter(company=employee.company, employee=employee, date=today).first()

    role_ids = effective_role_ids(employee)
    pending = ApprovalInstance.objects.filter(company=employee.company, status=ApprovalInstance.STATUS_PENDING)
    # Load every step once, so the loop below makes no query per request.
    steps = {(s.approval_chain_id, s.step_order): s for s in ApprovalStep.objects.filter(approval_chain__company=employee.company)}
    waiting = sum(
        1 for instance in pending
        if can_act(employee, instance, step=steps.get((instance.approval_chain_id, instance.current_step)), role_ids=role_ids)
    )

    by_status = _by_status(mine)
    return {
        'open_tasks': mine.exclude(status=Task.STATUS_COMPLETED).count(),
        'overdue_tasks': _overdue(mine, today),
        'tasks_by_status': by_status,
        'checked_in_today': record is not None,
        'checked_out_today': bool(record and record.check_out),
        'approvals_waiting': waiting,
    }


def team_section(employee, today):
    tasks = Task.objects.filter(company=employee.company)
    priorities = {row['priority']: row['n'] for row in tasks.values('priority').annotate(n=Count('id'))}
    by_status = _by_status(tasks)
    total = sum(by_status.values())
    completed = by_status[Task.STATUS_COMPLETED]
    return {
        'total_tasks': total,
        'overdue_tasks': _overdue(tasks, today),
        'awaiting_review': by_status[Task.STATUS_SUBMITTED],
        'completion_rate': round(completed * 100 / total, 1) if total else 0.0,
        'tasks_by_status': by_status,
        'tasks_by_priority': {p: priorities.get(p, 0) for p in PRIORITIES},
    }


def people_section(employee, today):
    company = employee.company
    employees = Employee.objects.filter(company=company)
    total = employees.count()
    present = Attendance.objects.filter(company=company, date=today).values('employee').distinct().count()

    by_department = Counter(
        employees.values_list('department__name', flat=True)
    )
    chart = [
        {'name': name or 'No department', 'count': count}
        for name, count in sorted(by_department.items(), key=lambda kv: (-kv[1], kv[0] or ''))
    ]
    month_start = today.replace(day=1)
    return {
        'total_employees': total,
        'new_this_month': employees.filter(created_at__date__gte=month_start).count(),
        'departments': Department.objects.filter(company=company).count(),
        'present_today': present,
        'attendance_rate': round(present * 100 / total, 1) if total else 0.0,
        'employees_by_department': chart,
    }


def finance_section(employee, today):
    company = employee.company
    structures = SalaryStructure.objects.filter(company=company)
    totals = structures.aggregate(total=Sum('base_salary'), average=Avg('base_salary'), n=Count('id'))
    headcount = Employee.objects.filter(company=company).count()

    per_department = {}
    for dept, amount in structures.values_list('employee__department__name', 'base_salary'):
        key = dept or 'No department'
        per_department[key] = per_department.get(key, Decimal(0)) + amount
    chart = [
        {'name': name, 'total': _money(total)}
        for name, total in sorted(per_department.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    settings = getattr(company, 'settings', None)
    return {
        'currency': getattr(settings, 'currency', 'BDT'),
        'salary_structures': totals['n'],
        'employees_without_salary': max(headcount - totals['n'], 0),
        'total_base_payroll': _money(totals['total']),
        'average_base_salary': _money(totals['average']),
        'payroll_by_department': chart,
    }


def build_summary(employee):
    """The dashboard for this employee: only the sections their Permissions allow."""
    today, _zone = local_today(employee.company)  # the day in the COMPANY's own time zone
    summary = {'me': me_section(employee, today)}
    if employee.has_permission(TEAM_PERMISSION):
        summary['team'] = team_section(employee, today)
    if employee.has_permission(PEOPLE_PERMISSION):
        summary['people'] = people_section(employee, today)
    if employee.has_permission(FINANCE_PERMISSION):
        summary['finance'] = finance_section(employee, today)
    return summary
