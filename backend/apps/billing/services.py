import calendar
import datetime
from decimal import Decimal

from django.db import transaction

from core.exceptions import OrdinisException
from .models import Invoice, Subscription, SubscriptionPlan

# The plans every company can choose from. Prices are placeholders until pricing is decided.
DEFAULT_PLANS = [
    ('Basic', 10, Decimal('1500.00')),
    ('Professional', 50, Decimal('5000.00')),
    ('Enterprise', None, Decimal('15000.00')),
]
STARTING_PLAN = 'Basic'


class PlanLimitError(OrdinisException):
    code = 'PLAN_LIMIT_REACHED'
    message = 'Your plan does not allow more employees. Upgrade your plan to add more.'
    status_code = 400


class BillingError(OrdinisException):
    code = 'BILLING_ERROR'
    message = 'The billing change could not be made.'
    status_code = 400


def seed_plans():
    for name, limit, price in DEFAULT_PLANS:
        SubscriptionPlan.objects.get_or_create(name=name, defaults={'max_employees': limit, 'price_monthly': price})


def start_subscription(company, plan_name=STARTING_PLAN):
    """Put a company on a plan (new companies start on Basic). Safe to call twice."""
    seed_plans()
    plan = SubscriptionPlan.objects.get(name=plan_name)
    subscription, _ = Subscription.objects.get_or_create(
        company=company, defaults={'plan': plan, 'started_on': datetime.date.today()},
    )
    return subscription


def get_subscription(company):
    """The company's subscription. A company that has none yet is put on Basic."""
    try:
        return company.subscription
    except Subscription.DoesNotExist:
        return start_subscription(company)


def employee_count(company):
    from organization.models import Employee
    return Employee.objects.filter(company=company).count()


def usage(company):
    subscription = get_subscription(company)
    limit = subscription.plan.max_employees
    count = employee_count(company)
    return {
        'employees': count,
        'limit': limit,
        'unlimited': limit is None,
        'remaining': None if limit is None else max(limit - count, 0),
        'percent': 0 if limit is None else min(round(count * 100 / limit), 100),
        'is_full': limit is not None and count >= limit,
    }


def can_add_employee(company):
    return not usage(company)['is_full']


def ensure_can_add_employee(company):
    """Call inside the transaction that creates the employee. Refuses with an upgrade message when the plan is full."""
    with transaction.atomic():
        subscription = Subscription.objects.select_for_update().select_related('plan').filter(company=company).first() \
            or get_subscription(company)
        limit = subscription.plan.max_employees
        count = employee_count(company)
        if limit is not None and count >= limit:
            noun = 'employee' if limit == 1 else 'employees'
            raise PlanLimitError(
                f'Your {subscription.plan.name} plan allows {limit} {noun} and you already have {count}. '
                'Upgrade your plan to add more.'
            )


def change_plan(company, plan_name):
    """Move a company to another plan. A plan that is too small for the current team is refused."""
    plan = SubscriptionPlan.objects.filter(name=plan_name, is_active=True).first()
    if plan is None:
        raise BillingError(f'There is no plan called "{plan_name}".', code='PLAN_NOT_FOUND')
    count = employee_count(company)
    if plan.max_employees is not None and count > plan.max_employees:
        raise BillingError(
            f'The {plan.name} plan allows {plan.max_employees} employees but the company has {count}. Remove some first.',
            code='PLAN_TOO_SMALL',
        )
    subscription = get_subscription(company)
    subscription.plan = plan
    subscription.save(update_fields=['plan', 'updated_at'])
    return subscription


def month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, 1), datetime.date(year, month, last)


def generate_invoice(subscription, year, month):
    """The invoice of one month at the plan's price now. A second call for the same month returns the same invoice."""
    start, end = month_bounds(year, month)
    existing = Invoice.objects.filter(subscription=subscription, period_start=start).first()
    if existing:
        return existing, False
    plan = subscription.plan
    number = f'INV-{year}{month:02d}-{str(subscription.company_id).replace("-", "")[:6].upper()}'
    invoice = Invoice.objects.create(
        company=subscription.company, subscription=subscription, number=number, plan_name=plan.name,
        period_start=start, period_end=end, amount=plan.price_monthly, currency=plan.currency,
        issued_on=start, due_on=start + datetime.timedelta(days=14),
    )
    return invoice, True


def mark_paid(invoice, on=None):
    if invoice.status == Invoice.STATUS_VOID:
        raise BillingError('A void invoice cannot be paid.', code='INVOICE_VOID')
    invoice.status = Invoice.STATUS_PAID
    invoice.paid_on = on or datetime.date.today()
    invoice.save(update_fields=['status', 'paid_on', 'updated_at'])
    return invoice
