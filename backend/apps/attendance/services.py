from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import IntegrityError, transaction
from django.utils import timezone

from tenants.models import CompanySettings
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
