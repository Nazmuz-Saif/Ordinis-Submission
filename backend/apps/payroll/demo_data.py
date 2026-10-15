from decimal import Decimal

from .models import SalaryStructure
from .services import PayslipError, generate_payslip

ORDER = 60

# key: base salary (BDT). Allowances are 40% house rent, 10% medical, 5% transport of the base.
BASE = {
    'ceo': 250000, 'gm': 160000, 'manager': 120000, 'sales_head': 110000, 'hr': 70000,
    'accountant': 65000, 'employee': 75000, 'dev2': 72000, 'designer': 60000, 'sales1': 45000,
}
DEDUCTIONS = {('employee', 1): (Decimal('2500'), 'Unpaid leave (1 day)'), ('sales1', 2): (Decimal('1500'), 'Late arrivals')}


def _months_back(today, count):
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        months.append((year, month))
    return months


def seed(ctx):
    company = ctx.company
    for key, base in BASE.items():
        base = Decimal(base)
        _, created = SalaryStructure.objects.get_or_create(
            company=company, employee=ctx.emp(key),
            defaults={
                'base_salary': base,
                'allowances': {
                    'House Rent': float(base * Decimal('0.40')), 'Medical': float(base * Decimal('0.10')),
                    'Transport': float(base * Decimal('0.05')),
                },
            },
        )
        ctx.note('salary structures', created)

    for ago, (year, month) in enumerate(_months_back(ctx.today, 3)):   # the last three finished months
        for key in BASE:
            deduction, note = DEDUCTIONS.get((key, ago), (0, ''))
            try:
                generate_payslip(ctx.emp('accountant'), ctx.emp(key), year, month, deduction, note)
                ctx.note('payslips', True)
            except PayslipError as exc:
                if exc.code != 'PAYSLIP_ALREADY_EXISTS':
                    raise
