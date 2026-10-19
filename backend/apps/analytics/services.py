"""
Company health numbers (ST-134, FR-32). Every number comes from the real attendance and task rows
of ONE company, and the day is the day in that company's own time zone.

How the numbers are calculated:

  working day       a day on which at least one employee checked in. This follows the company's real
                    week (Friday and Saturday, holidays) without any setting, because a Holiday Calendar
                    does not exist yet.
  attendance rate   present employee-days / expected employee-days, for the working days of the month.
                    expected = employees x working days - employee-days on Approved leave (a person on
                    approved leave who did not check in is not expected). A month with no working day is 0.
                    Limit: the head count is the head count NOW, not the one of that past month.
  completion rate   Completed tasks / all tasks of the company. No task is 0.
  overdue tasks     deadline before today and not Completed.
  average workload  tasks that are not Completed, per employee.
"""
import calendar
import datetime
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Q

from attendance.leave_models import LeaveRequest
from attendance.models import Attendance
from attendance.services import local_today
from organization.models import Employee
from tasks.models import Task

from .models import CompanyHealthSnapshot

MONTHS = 6
NO_DEPARTMENT = 'No department'


def _pct(part, whole):
    """A percentage with one decimal, never above 100, 0 when there is nothing to divide by."""
    if whole <= 0:
        return 0.0
    return round(min(part * 100 / whole, 100), 1)


def _month_list(today, count=MONTHS):
    """[(year, month)] of the last `count` months, the oldest first, the current month last."""
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        months.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


def _approved_leaves(company, start, end):
    return list(
        LeaveRequest.objects.filter(
            company=company, status=LeaveRequest.STATUS_APPROVED, start_date__lte=end, end_date__gte=start,
        ).values_list('employee_id', 'start_date', 'end_date')
    )


def _leave_employee_days(leaves, working_days, attended):
    """
    Employee-days that are on Approved leave on a working day AND had no check-in.
    `attended` is a set of (employee_id, date). Overlapping leaves of one person count once per day.
    """
    counted = set()
    for employee_id, first, last in leaves:
        for day in working_days:
            if first <= day <= last and (employee_id, day) not in attended:
                counted.add((employee_id, day))
    return len(counted)


def attendance_by_month(company, today, headcount):
    """[{month, short, label, rate, working_days}] for the last 6 months. A month without data is rate 0."""
    months = _month_list(today)
    first_year, first_month = months[0]
    start = datetime.date(first_year, first_month, 1)

    per_day = {
        row['date']: row['n']
        for row in Attendance.objects.filter(company=company, date__gte=start, date__lte=today)
        .values('date').annotate(n=Count('id'))
    }
    leaves = _approved_leaves(company, start, today)
    attended = set()
    if leaves:
        attended = set(
            Attendance.objects.filter(
                company=company, date__gte=start, date__lte=today,
                employee_id__in={employee_id for employee_id, _first, _last in leaves},
            ).values_list('employee_id', 'date')
        )

    result = []
    for year, month in months:
        days = {d for d in per_day if d.year == year and d.month == month}
        present = sum(per_day[d] for d in days)
        if days and headcount:
            on_leave = _leave_employee_days(leaves, days, attended)
            rate = _pct(present, headcount * len(days) - on_leave)
        else:
            rate = 0.0
        result.append({
            'month': f'{year}-{month:02d}',
            'short': calendar.month_abbr[month],
            'label': f'{calendar.month_name[month]} {year}',
            'rate': rate,
            'working_days': len(days),
        })
    return result


def task_numbers(company, today, headcount):
    tasks = Task.objects.filter(company=company)
    total = tasks.count()
    completed = tasks.filter(status=Task.STATUS_COMPLETED).count()
    open_tasks = total - completed
    overdue = tasks.filter(deadline__lt=today).exclude(status=Task.STATUS_COMPLETED).count()
    return {
        'total': total,
        'completed': completed,
        'open': open_tasks,
        'overdue': overdue,
        'completion_rate': _pct(completed, total),
        'avg_workload': round(open_tasks / headcount, 1) if headcount else 0.0,
    }


def tasks_by_department(company):
    """[{name, completed, pending}] for the grouped bar chart. pending = every task that is not Completed."""
    rows = (
        Task.objects.filter(company=company)
        .values('assigned_to__department__name')
        .annotate(
            completed=Count('id', filter=Q(status=Task.STATUS_COMPLETED)),
            pending=Count('id', filter=~Q(status=Task.STATUS_COMPLETED)),
        )
    )
    merged = defaultdict(lambda: [0, 0])
    for row in rows:
        name = row['assigned_to__department__name'] or NO_DEPARTMENT
        merged[name][0] += row['completed']
        merged[name][1] += row['pending']
    ordered = sorted(merged.items(), key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0]))
    return [{'name': name, 'completed': done, 'pending': pending} for name, (done, pending) in ordered]


def overview(company):
    """Everything the Analytics page shows, in one dict."""
    today, _zone = local_today(company)
    headcount = Employee.objects.filter(company=company).count()
    months = attendance_by_month(company, today, headcount)
    tasks = task_numbers(company, today, headcount)

    this_month, last_month = months[-1], months[-2]
    change = None
    if this_month['working_days'] and last_month['working_days']:
        change = round(this_month['rate'] - last_month['rate'], 1)

    departments = tasks_by_department(company)
    return {
        'as_of': today.isoformat(),
        'headcount': headcount,
        'metrics': {
            'attendance_rate': this_month['rate'],
            'attendance_rate_change': change,
            'task_completion_rate': tasks['completion_rate'],
            'overdue_tasks': tasks['overdue'],
            'average_workload': tasks['avg_workload'],
        },
        'attendance_by_month': months,
        'tasks_by_department': departments,
        'has_data': bool(tasks['total'] or any(m['working_days'] for m in months)),
    }


def _day_attendance_rate(company, day, headcount):
    present = Attendance.objects.filter(company=company, date=day).count()
    on_leave = (
        LeaveRequest.objects.filter(
            company=company, status=LeaveRequest.STATUS_APPROVED, start_date__lte=day, end_date__gte=day,
        )
        .exclude(employee__attendance_records__date=day)
        .values('employee').distinct().count()
    )
    return _pct(present, headcount - on_leave)


def take_snapshot(company, day=None):
    """
    Stores (or refreshes) the health snapshot of one company for one day. Safe to run twice: one row per day.
    Returns (snapshot, created).
    """
    if day is None:
        day, _zone = local_today(company)
    headcount = Employee.objects.filter(company=company).count()
    tasks = task_numbers(company, day, headcount)
    attendance = _day_attendance_rate(company, day, headcount)
    score = round((attendance + tasks['completion_rate']) / 2, 1)
    return CompanyHealthSnapshot.objects.update_or_create(
        company=company, date=day,
        defaults={
            'headcount': headcount,
            'attendance_rate': Decimal(str(attendance)),
            'task_completion_rate': Decimal(str(tasks['completion_rate'])),
            'open_tasks': tasks['open'],
            'overdue_tasks': tasks['overdue'],
            'health_score': Decimal(str(score)),
        },
    )
