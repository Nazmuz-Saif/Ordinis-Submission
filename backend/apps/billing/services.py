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

# ---- Subscription period rules. One place to change them. ----
GRACE_DAYS = 3                 # days after the end date the company still works (with a warning banner)
REMINDER_DAYS = (7, 3, 1)      # in-app reminders this many days before the end
DEFAULT_MONTHS = 12            # length of the period a company gets when it is started without a payment (registration, demo)

# Effective states, as shown to the frontend
STATE_PENDING_PAYMENT = 'pending_payment'
STATE_ACTIVE = 'active'
STATE_GRACE = 'grace'
STATE_EXPIRED = 'expired'
STATE_CANCELLED = 'cancelled'


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


def add_months(day, months):
    """`day` plus whole months; the day number is cut to the last day of a shorter month (31 Jan + 1 month = 28/29 Feb)."""
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return datetime.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def period_end_for(start, months):
    """The LAST day of a period of `months` months that begins on `start`."""
    return add_months(start, months) - datetime.timedelta(days=1)


def start_subscription(company, plan_name=STARTING_PLAN, months=DEFAULT_MONTHS, status=Subscription.STATUS_ACTIVE):
    """Put a company on a plan (new companies start on Basic). Safe to call twice."""
    seed_plans()
    plan = SubscriptionPlan.objects.get(name=plan_name)
    today = datetime.date.today()
    subscription, _ = Subscription.objects.get_or_create(
        company=company,
        defaults={
            'plan': plan, 'status': status, 'started_on': today, 'billing_months': months,
            'current_period_start': today, 'current_period_end': period_end_for(today, months),
        },
    )
    return subscription


def set_period(subscription, start, months):
    """Give the subscription a new paid period and forget the reminders of the old one. The caller saves."""
    subscription.current_period_start = start
    subscription.current_period_end = period_end_for(start, months)
    subscription.billing_months = months
    subscription.reminders_sent = []
    return subscription


# ---------- Days left, state, restricted mode ----------

def _today(company):
    from attendance.services import local_today
    return local_today(company)[0]


def days_left(subscription, today=None):
    """End date minus the company's own today. Never stored. 0 on the last day, negative after it."""
    today = today or _today(subscription.company)
    return (subscription.current_period_end - today).days


def effective_state(subscription, today=None):
    """What the company can do right now. Works even when the daily job did not run."""
    if subscription.status == Subscription.STATUS_PENDING_PAYMENT:
        return STATE_PENDING_PAYMENT
    if subscription.status == Subscription.STATUS_EXPIRED:
        return STATE_EXPIRED
    if subscription.status == Subscription.STATUS_CANCELLED:
        return STATE_CANCELLED
    left = days_left(subscription, today)
    if left >= 0:
        return STATE_ACTIVE
    return STATE_GRACE if left >= -GRACE_DAYS else STATE_EXPIRED


def is_restricted(subscription, today=None):
    return effective_state(subscription, today) in (STATE_PENDING_PAYMENT, STATE_EXPIRED)


def restriction_for(company):
    """The state name when the company is in restricted mode, else None. Used on every request: one query,
    and no time zone lookup while the end date is clearly far away."""
    subscription = Subscription.objects.filter(company=company).first()
    if subscription is None:
        return None
    if subscription.status == Subscription.STATUS_ACTIVE:
        # Time zones differ by less than 2 days from UTC, so a far end date needs no exact check.
        from attendance.services import _now
        if subscription.current_period_end - _now().date() > datetime.timedelta(days=2):
            return None
    state = effective_state(subscription)
    return state if state in (STATE_PENDING_PAYMENT, STATE_EXPIRED) else None


def subscription_summary(company):
    """What the frontend needs for the banner and the route guard (sent inside /auth/me/)."""
    subscription = Subscription.objects.filter(company=company).select_related('plan').first()
    if subscription is None:
        return None
    state = effective_state(subscription)
    return {
        'status': state,
        'restricted': state in (STATE_PENDING_PAYMENT, STATE_EXPIRED),
        'days_left': days_left(subscription),
        'period_start': subscription.current_period_start,
        'period_end': subscription.current_period_end,
        'billing_months': subscription.billing_months,
        'grace_days': GRACE_DAYS,
        'plan': subscription.plan.name,
    }


# ---------- The daily job ----------

def _billing_recipients(company):
    """The CEO and everyone who holds view_billing (the CEO role holds every Permission). Nobody twice."""
    from organization.models import Employee
    return Employee.objects.filter(
        company=company, employee_roles__role__permissions__codename='view_billing',
    ).select_related('user').distinct()


def send_reminder(subscription, left):
    from notifications.models import Notification
    from notifications.services import notify
    noun = 'day' if left == 1 else 'days'
    when = 'ends today' if left == 0 else f'ends in {left} {noun}'
    sent = 0
    for employee in _billing_recipients(subscription.company):
        notify(
            employee, Notification.KIND_BILLING_REMINDER, f'Your subscription {when}',
            f'The {subscription.plan.name} plan {when} (on {subscription.current_period_end}). '
            'Renew to keep using Ordinis.', '/settings/billing',
        )
        sent += 1
    return sent


def process_subscription(subscription, today=None):
    """One company's daily work. Running it twice in a row changes nothing more.
    Returns (reminder_sent, expired)."""
    company = subscription.company
    today = today or _today(company)
    left = days_left(subscription, today)
    if left < -GRACE_DAYS:
        subscription.status = Subscription.STATUS_EXPIRED
        subscription.save(update_fields=['status', 'updated_at'])
        return False, True
    if left < 0 or not company.is_active:
        return False, False          # in grace (banner only), or suspended: nobody to remind
    # A reminder is due for every threshold we have reached. A missed day is not a lost reminder:
    # the first run after the threshold sends ONE message and marks every reached threshold as sent.
    reached = [t for t in REMINDER_DAYS if left <= t]
    sent = list(subscription.reminders_sent or [])
    if not reached or all(t in sent for t in reached):
        return False, False
    send_reminder(subscription, left)
    subscription.reminders_sent = sorted(set(sent) | set(reached))
    subscription.save(update_fields=['reminders_sent', 'updated_at'])
    return True, False


def process_subscriptions():
    """The daily job for every active subscription. One company's error never stops the others."""
    result = {'checked': 0, 'reminded': 0, 'expired': 0, 'errors': 0}
    for subscription in Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).select_related('company', 'plan'):
        result['checked'] += 1
        try:
            with transaction.atomic():
                subscription = Subscription.objects.select_for_update().select_related('company', 'plan').get(pk=subscription.pk)
                if subscription.status != Subscription.STATUS_ACTIVE:
                    continue
                reminded, expired = process_subscription(subscription)
        except Exception:      # noqa: BLE001  one bad company must not stop the rest
            import logging
            logging.getLogger(__name__).exception('process_subscriptions failed for %s', subscription.company_id)
            result['errors'] += 1
            continue
        result['reminded'] += reminded
        result['expired'] += expired
    return result


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
