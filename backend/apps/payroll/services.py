from decimal import Decimal


def gross_amount(structure):
    """Base salary plus all allowances."""
    return structure.base_salary + sum((Decimal(str(v)) for v in structure.allowances.values()), Decimal('0'))


# ---------- Payslips (ST-127) ----------
import calendar  # noqa: E402

from django.db import IntegrityError, transaction  # noqa: E402

from core.exceptions import OrdinisException  # noqa: E402
from .models import Payslip, SalaryStructure  # noqa: E402

MONEY = Decimal('0.01')


class PayslipError(OrdinisException):
    code = 'PAYSLIP_ERROR'
    message = 'The payslip could not be generated.'
    status_code = 400


def month_label(year, month):
    return f'{calendar.month_name[month]} {year}'


def generate_payslip(actor, employee, year, month, deductions=0, deduction_note=''):
    """
    Create the payslip of `employee` for year/month from their Salary Structure.
    Refuses: no Salary Structure, a month that has not started, bad deductions, a second payslip for the month.
    """
    from attendance.services import local_today

    if not 1 <= month <= 12:
        raise PayslipError('The month must be between 1 and 12.', code='PAYSLIP_BAD_MONTH')
    today, _zone = local_today(employee.company)
    if (year, month) > (today.year, today.month):
        raise PayslipError(
            f'{month_label(year, month)} has not started yet, so it cannot have a payslip.', code='PAYSLIP_FUTURE_MONTH',
        )

    structure = SalaryStructure.objects.filter(company_id=employee.company_id, employee=employee).first()
    if structure is None:
        raise PayslipError(
            f'{employee.user.email} has no salary structure yet. Set one up first, then generate the payslip.',
            code='PAYSLIP_NO_SALARY_STRUCTURE',
        )

    gross = gross_amount(structure).quantize(MONEY)
    deductions = Decimal(str(deductions or 0)).quantize(MONEY)
    if deductions < 0:
        raise PayslipError('Deductions cannot be negative.', code='PAYSLIP_BAD_DEDUCTIONS')
    if deductions > gross:
        raise PayslipError(
            f'Deductions ({deductions}) cannot be more than the gross amount ({gross}).', code='PAYSLIP_BAD_DEDUCTIONS',
        )

    duplicate = PayslipError(
        f'A payslip for {employee.user.email} for {month_label(year, month)} already exists.', code='PAYSLIP_ALREADY_EXISTS',
    )
    if Payslip.objects.filter(employee=employee, year=year, month=month).exists():
        raise duplicate
    try:
        with transaction.atomic():
            return Payslip.objects.create(
                company_id=employee.company_id, employee=employee, year=year, month=month,
                base_salary=structure.base_salary, allowances=dict(structure.allowances),
                gross_amount=gross, deductions=deductions, deduction_note=(deduction_note or '').strip(),
                net_amount=gross - deductions, generated_by=actor,
            )
    except IntegrityError:          # two people pressed Generate at the same moment: the database says no
        raise duplicate
