import calendar
import datetime
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import IntegrityError, transaction
from django.utils import timezone

from tenants.models import CompanySettings
from .leave_models import LeaveRequest
from .models import Attendance


class AttendanceError(ValueError):
    """A check-in / check-out that is not allowed (duplicate, out of order)."""


def _now():
    return timezone.now()


def company_zone(company):
    """The company's own time zone; falls back to the project default if the setting is missing or invalid."""
    settings = CompanySettings.objects.filter(company=company).first()
    name = settings.timezone if settings else None
    try:
        return ZoneInfo(name) if name else timezone.get_default_timezone()
    except ZoneInfoNotFoundError:
        return timezone.get_default_timezone()


def local_today(company):
    """(today's date in the company's time zone, the zone)."""
    zone = company_zone(company)
    return _now().astimezone(zone).date(), zone


def get_today(employee):
    today, _ = local_today(employee.company)
    return Attendance.objects.filter(employee=employee, date=today).first()


def check_in(employee):
    today, _ = local_today(employee.company)
    try:
        with transaction.atomic():
            return Attendance.objects.create(
                company=employee.company, employee=employee, date=today, check_in=_now(),
            )
    except IntegrityError:
        raise AttendanceError('You have already checked in today.')


@transaction.atomic
def check_out(employee):
    today, _ = local_today(employee.company)
    record = Attendance.objects.select_for_update().filter(employee=employee, date=today).first()
    if record is None:
        raise AttendanceError('You have not checked in today. Check in first.')
    if record.check_out is not None:
        raise AttendanceError('You have already checked out today.')
    record.check_out = _now()
    record.save(update_fields=['check_out', 'updated_at'])
    return record


MONTH_PATTERN = re.compile(r'^(\d{4})-(0[1-9]|1[0-2])$')
MIN_YEAR = 2000


def _parse_month(text, today):
    if not text:
        return today.year, today.month
    match = MONTH_PATTERN.match(text)
    if not match or int(match.group(1)) < MIN_YEAR:
        raise AttendanceError('The month must look like 2026-10.')
    return int(match.group(1)), int(match.group(2))


def _month_key(year, month):
    return f'{year}-{month:02d}'


def month_calendar(employee, month=None):
    """
    ST-137: one month of the employee's OWN attendance, a status for each day, and the month's summary.

    A day's status, first rule that matches:
      after today                           no status
      the employee has a check-in           present
      nobody in the company checked in      no status (a weekend or a holiday; there is no Holiday Calendar)
      Approved leave covers the day         on_leave
      the day is today                      no status yet (the day is not over)
      otherwise                             absent
    Attendance rate = present / (present + absent): leave days are not expected. No such day is 0.
    """
    company = employee.company
    today, _zone = local_today(company)
    year, mon = _parse_month(month, today)
    first = datetime.date(year, mon, 1)
    last = datetime.date(year, mon, calendar.monthrange(year, mon)[1])
    until = min(last, today)

    mine = set()
    working_days = set()
    leaves = []
    if first <= today:
        mine = set(Attendance.objects.filter(employee=employee, date__range=(first, until)).values_list('date', flat=True))
        working_days = set(Attendance.objects.filter(company=company, date__range=(first, until)).values_list('date', flat=True))
        leaves = list(
            LeaveRequest.objects.filter(
                employee=employee, status=LeaveRequest.STATUS_APPROVED, start_date__lte=until, end_date__gte=first,
            ).values_list('start_date', 'end_date')
        )

    days = []
    counts = {'present': 0, 'absent': 0, 'on_leave': 0}
    for number in range(1, last.day + 1):
        day = datetime.date(year, mon, number)
        status = None
        if day <= today:
            if day in mine:
                status = 'present'
            elif day in working_days:
                if any(start <= day <= end for start, end in leaves):
                    status = 'on_leave'
                elif day != today:
                    status = 'absent'
        if status:
            counts[status] += 1
        days.append({'date': day.isoformat(), 'status': status})

    expected = counts['present'] + counts['absent']
    rate = round(counts['present'] * 100 / expected, 1) if expected else 0.0
    previous = (year, mon - 1) if mon > 1 else (year - 1, 12)
    following = (year, mon + 1) if mon < 12 else (year + 1, 1)
    return {
        'month': _month_key(year, mon),
        'label': f'{calendar.month_name[mon]} {year}',
        'previous': _month_key(*previous) if previous[0] >= MIN_YEAR else None,
        'next': _month_key(*following) if following <= (today.year, today.month) else None,
        'first_weekday': first.weekday(),          # 0 = Monday, so the grid knows where day 1 sits
        'days': days,
        'summary': {
            'present': counts['present'], 'absent': counts['absent'], 'on_leave': counts['on_leave'],
            'attendance_rate': rate,
        },
    }
