import calendar
import datetime
from decimal import ROUND_HALF_UP, Decimal

import re
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from core.exceptions import OrdinisException
from .models import Invoice, PaymentSubmission, Subscription, SubscriptionPlan

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
RENEWAL_INVOICE_DAYS = 7       # the renewal invoice is issued this many days before the end
MIN_MONTHS, MAX_MONTHS = 1, 36  # how many months one payment can buy
FREE_MONTHS_PER_YEAR = 2        # every full 12 months costs 10: 12 months = price of 10, 24 = 20, 36 = 30
UPGRADE_DAYS_IN_MONTH = 30      # the extra amount of an upgrade = price difference x days left / 30
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
    invoice = open_renewal_invoice(subscription)
    bill = f' Invoice {invoice.number} for {invoice.amount} {invoice.currency} is ready.' if invoice else ''
    sent = 0
    for employee in _billing_recipients(subscription.company):
        notify(
            employee, Notification.KIND_BILLING_REMINDER, f'Your subscription {when}',
            f'The {subscription.plan.name} plan {when} (on {subscription.current_period_end}). '
            f'Renew to keep using Ordinis.{bill}', '/settings/billing',
        )
        sent += 1
    return sent


def process_subscription(subscription, today=None):
    """One company's daily work. Running it twice in a row changes nothing more.
    Returns (reminder_sent, expired, invoice_issued)."""
    company = subscription.company
    today = today or _today(company)
    apply_scheduled_plan(subscription, today)
    left = days_left(subscription, today)
    if left < -GRACE_DAYS:
        subscription.status = Subscription.STATUS_EXPIRED
        subscription.save(update_fields=['status', 'updated_at'])
        return False, True, False
    invoiced = ensure_renewal_invoice(subscription, left, today) if left <= RENEWAL_INVOICE_DAYS else False
    if left < 0 or not company.is_active:
        return False, False, invoiced          # in grace (banner only), or suspended: nobody to remind
    # A reminder is due for every threshold we have reached. A missed day is not a lost reminder:
    # the first run after the threshold sends ONE message and marks every reached threshold as sent.
    reached = [t for t in REMINDER_DAYS if left <= t]
    sent = list(subscription.reminders_sent or [])
    if not reached or all(t in sent for t in reached):
        return False, False, invoiced
    send_reminder(subscription, left)
    subscription.reminders_sent = sorted(set(sent) | set(reached))
    subscription.save(update_fields=['reminders_sent', 'updated_at'])
    return True, False, invoiced


def process_subscriptions():
    """The daily job for every active subscription. One company's error never stops the others."""
    result = {'checked': 0, 'reminded': 0, 'expired': 0, 'invoiced': 0, 'errors': 0}
    for subscription in Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).select_related('company', 'plan'):
        result['checked'] += 1
        try:
            with transaction.atomic():
                subscription = Subscription.objects.select_for_update().select_related('company', 'plan').get(pk=subscription.pk)
                if subscription.status != Subscription.STATUS_ACTIVE:
                    continue
                reminded, expired, invoiced = process_subscription(subscription)
        except Exception:      # noqa: BLE001  one bad company must not stop the rest
            import logging
            logging.getLogger(__name__).exception('process_subscriptions failed for %s', subscription.company_id)
            result['errors'] += 1
            continue
        result['reminded'] += reminded
        result['expired'] += expired
        result['invoiced'] += invoiced
    return result


def get_subscription(company):
    """The company's subscription. A company that has none yet is put on Basic.
    A lower plan that was scheduled for a period that has now begun starts here (the daily job does the same)."""
    try:
        subscription = company.subscription
    except Subscription.DoesNotExist:
        return start_subscription(company)
    if subscription.next_plan_id and subscription.next_plan_from:
        apply_scheduled_plan(subscription, _today(company))
    return subscription


def apply_scheduled_plan(subscription, today):
    """Start the lower plan the company chose, once the period it was bought for has begun. True when it changed."""
    if not (subscription.next_plan_id and subscription.next_plan_from) or today < subscription.next_plan_from:
        return False
    subscription.plan = subscription.next_plan
    subscription.next_plan, subscription.next_plan_from = None, None
    subscription.save(update_fields=['plan', 'next_plan', 'next_plan_from', 'updated_at'])
    return True


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


def open_renewal_invoice(subscription):
    """The renewal invoice waiting to be paid, if there is one."""
    return Invoice.objects.filter(
        subscription=subscription, kind=Invoice.KIND_RENEWAL, status=Invoice.STATUS_OPEN,
    ).order_by('-period_start').first()


def ensure_renewal_invoice(subscription, left, today):
    """Issue the renewal invoice once, RENEWAL_INVOICE_DAYS before the end (or later, if the job missed those days).
    It bills the next period of the same plan and the same length as the last payment, due on the end date.
    Nothing is issued while a payment is already waiting for approval. Returns True when an invoice was issued."""
    start = subscription.current_period_end + datetime.timedelta(days=1)
    if Invoice.objects.filter(subscription=subscription, kind=Invoice.KIND_RENEWAL, period_start=start).exists():
        return False
    if PaymentSubmission.objects.filter(company=subscription.company, status=PaymentSubmission.STATUS_PENDING).exists():
        return False
    months = min(max(subscription.billing_months or DEFAULT_MONTHS, MIN_MONTHS), MAX_MONTHS)
    plan = subscription.next_plan or subscription.plan      # a scheduled lower plan is what the renewal bills
    for _ in range(5):
        try:
            with transaction.atomic():
                Invoice.objects.create(
                    company=subscription.company, subscription=subscription, number=next_invoice_number(today),
                    plan_name=plan.name, period_start=start, period_end=period_end_for(start, months),
                    amount=price_for(plan, months)['amount'], currency=plan.currency, status=Invoice.STATUS_OPEN,
                    issued_on=today, due_on=subscription.current_period_end, kind=Invoice.KIND_RENEWAL, months=months,
                )
            return True
        except IntegrityError:
            if Invoice.objects.filter(subscription=subscription, period_start=start).exists():
                return False      # another run issued it at the same moment
    return False


# ---------- Price, quote and payments (ST-146) ----------

TRANSACTION_ID_RE = re.compile(r'^[A-Z0-9][A-Z0-9._\-]{3,63}$')
PAYER_NUMBER_RE = re.compile(r'^[0-9+][0-9 +\-]{4,29}$')
MONEY = Decimal('0.01')


def parse_months(value):
    """A whole number from MIN_MONTHS to MAX_MONTHS. Anything else is refused."""
    if isinstance(value, bool) or value is None or str(value).strip() == '':
        raise BillingError('Choose how many months to pay for.', code='MONTHS_INVALID')
    try:
        months = int(str(value).strip())
    except ValueError:
        raise BillingError('Months must be a whole number.', code='MONTHS_INVALID') from None
    if not MIN_MONTHS <= months <= MAX_MONTHS:
        raise BillingError(f'Choose between {MIN_MONTHS} and {MAX_MONTHS} months.', code='MONTHS_OUT_OF_RANGE')
    return months


def price_for(plan, months):
    """Plan price x months, minus FREE_MONTHS_PER_YEAR free months for every full 12 months. All on the server."""
    monthly = plan.price_monthly
    free_months = (months // 12) * FREE_MONTHS_PER_YEAR
    gross = (monthly * months).quantize(MONEY)
    discount = (monthly * free_months).quantize(MONEY)
    return {'monthly_price': monthly, 'gross': gross, 'discount': discount, 'free_months': free_months, 'amount': gross - discount}


def find_plan(reference):
    """An active plan by name or id."""
    reference = str(reference or '').strip()
    plan = None
    if reference:
        try:
            plan = SubscriptionPlan.objects.filter(is_active=True, id=uuid.UUID(reference)).first()
        except ValueError:
            plan = SubscriptionPlan.objects.filter(is_active=True, name__iexact=reference).first()
    if plan is None:
        raise BillingError('Choose one of the available plans.', code='PLAN_NOT_FOUND')
    return plan


def payment_context(subscription, plan, today=None):
    """What kind of payment this would be and where its period starts, for the company's state right now.
    A renewal of a running plan starts the day after the old end date, so no days are lost. An expired or
    waiting company starts today. A running plan cannot be switched by a renewal (that is the upgrade flow)."""
    today = today or _today(subscription.company)
    state = effective_state(subscription, today)
    if state in (STATE_ACTIVE, STATE_GRACE):
        if plan.id not in (subscription.plan_id, subscription.next_plan_id):
            raise BillingError(
                'A renewal keeps your current plan. To change the plan, use Change plan.', code='PLAN_CHANGE_NOT_VIA_RENEWAL',
            )
        kind, start = PaymentSubmission.KIND_RENEWAL, subscription.current_period_end + datetime.timedelta(days=1)
    elif state == STATE_EXPIRED:
        kind, start = PaymentSubmission.KIND_RENEWAL, today
    else:      # waiting for the first payment, or cancelled
        kind, start = PaymentSubmission.KIND_NEW, today
    count = employee_count(subscription.company)
    if plan.max_employees is not None and count > plan.max_employees:
        raise BillingError(
            f'The {plan.name} plan allows {plan.max_employees} employees but the company has {count}. Choose a bigger plan.',
            code='PLAN_TOO_SMALL',
        )
    return kind, start


def quote(company, plan_reference, months):
    """The amount, the discount and the period for a payment. Nothing is saved."""
    plan = find_plan(plan_reference)
    months = parse_months(months)
    subscription = get_subscription(company)
    kind, start = payment_context(subscription, plan)
    price = price_for(plan, months)
    return {
        'plan': {'id': plan.id, 'name': plan.name, 'max_employees': plan.max_employees, 'unlimited': plan.max_employees is None},
        'months': months, 'currency': plan.currency, 'kind': kind,
        'period_start': start, 'period_end': period_end_for(start, months), **price,
    }


def _team_fits(company, plan):
    count = employee_count(company)
    if plan.max_employees is not None and count > plan.max_employees:
        raise BillingError(
            f'The {plan.name} plan allows {plan.max_employees} employees but the company has {count}. Choose a bigger plan.',
            code='PLAN_TOO_SMALL',
        )


def _running_subscription(company, action):
    """The subscription, when its paid period is still running (today <= end date). Else a clear refusal."""
    subscription = get_subscription(company)
    today = _today(company)
    if effective_state(subscription, today) != STATE_ACTIVE:
        raise BillingError(
            f'Your plan period is not running, so you cannot {action}. Renew or pay for your plan first.',
            code='PLAN_CHANGE_NOT_AVAILABLE',
        )
    return subscription, today


def upgrade_amount(current_plan, new_plan, left):
    """(new monthly price - current monthly price) x days left / 30, rounded to a whole taka. Nothing is saved."""
    extra = (new_plan.price_monthly - current_plan.price_monthly) * left / UPGRADE_DAYS_IN_MONTH
    return extra.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def upgrade_quote(company, plan_reference):
    """What moving to a HIGHER plan costs now. The end date does not change. Nothing is saved."""
    plan = find_plan(plan_reference)
    subscription, today = _running_subscription(company, 'change your plan')
    current = subscription.plan
    if plan.price_monthly <= current.price_monthly:
        raise BillingError(
            f'The {plan.name} plan is not higher than your {current.name} plan. A lower plan starts at your next renewal.',
            code='UPGRADE_NOT_HIGHER',
        )
    left = days_left(subscription, today)
    amount = upgrade_amount(current, plan, left)
    if left < 1 or amount <= 0:
        raise BillingError(
            'Your current period ends today, so there is nothing to charge for the days left. '
            'Renew your plan first, then change it.', code='UPGRADE_NO_DAYS_LEFT',
        )
    return {
        'plan': {'id': plan.id, 'name': plan.name, 'max_employees': plan.max_employees, 'unlimited': plan.max_employees is None},
        'current_plan': {'id': current.id, 'name': current.name},
        'kind': PaymentSubmission.KIND_UPGRADE, 'currency': plan.currency, 'amount': amount,
        'monthly_price': plan.price_monthly, 'current_monthly_price': current.price_monthly,
        'days_left': left, 'days_in_month': UPGRADE_DAYS_IN_MONTH,
        'months': min(max(subscription.billing_months or DEFAULT_MONTHS, MIN_MONTHS), MAX_MONTHS),
        'period_start': today, 'period_end': subscription.current_period_end,
    }


def _reprice_open_renewal(subscription, plan):
    """The renewal invoice that is waiting must bill the plan that will start next."""
    invoice = open_renewal_invoice(subscription)
    if invoice is None or invoice.plan_name == plan.name:
        return
    invoice.plan_name, invoice.currency = plan.name, plan.currency
    invoice.amount = price_for(plan, invoice.months)['amount']
    invoice.save(update_fields=['plan_name', 'currency', 'amount', 'updated_at'])


@transaction.atomic
def schedule_downgrade(company, plan_reference):
    """Choose a LOWER plan. It starts at the next renewal, not now, and only if the team fits in it."""
    plan = find_plan(plan_reference)
    subscription = Subscription.objects.select_for_update().select_related('plan').get(pk=get_subscription(company).pk)
    _running_subscription(company, 'schedule a lower plan')
    if plan.price_monthly >= subscription.plan.price_monthly:
        raise BillingError(
            f'The {plan.name} plan is not lower than your {subscription.plan.name} plan. Use the upgrade for a higher plan.',
            code='DOWNGRADE_NOT_LOWER',
        )
    _team_fits(company, plan)
    subscription.next_plan, subscription.next_plan_from = plan, None
    subscription.save(update_fields=['next_plan', 'next_plan_from', 'updated_at'])
    _reprice_open_renewal(subscription, plan)
    return subscription


@transaction.atomic
def cancel_downgrade(company):
    """Stay on the current plan: forget the lower plan that was chosen. Only before its renewal has been paid."""
    subscription = Subscription.objects.select_for_update().select_related('plan').get(pk=get_subscription(company).pk)
    if subscription.next_plan_id is None:
        raise BillingError('No lower plan is scheduled.', code='DOWNGRADE_NOT_SCHEDULED')
    if subscription.next_plan_from is not None:
        raise BillingError('The lower plan is already paid for the next period. It cannot be cancelled now.', code='DOWNGRADE_ALREADY_PAID')
    subscription.next_plan = None
    subscription.save(update_fields=['next_plan', 'updated_at'])
    _reprice_open_renewal(subscription, subscription.plan)
    return subscription


def _clean_transaction_id(value):
    cleaned = re.sub(r'\s+', '', str(value or '')).upper()
    if not TRANSACTION_ID_RE.match(cleaned):
        raise BillingError(
            'Enter the transaction id exactly as your payment receipt shows it (4 to 64 letters or digits).',
            code='TRANSACTION_ID_INVALID', field_errors={'transaction_id': ['Enter a valid transaction id.']},
        )
    return cleaned


def _clean_payer(name, number):
    name, number = str(name or '').strip(), str(number or '').strip()
    if not name or len(name) > 100:
        raise BillingError('Enter the name of the person who paid.', code='PAYER_NAME_INVALID', field_errors={'payer_name': ['This field is required.']})
    if not PAYER_NUMBER_RE.match(number):
        raise BillingError(
            'Enter the number the payment came from (digits, 5 to 30 characters).', code='PAYER_NUMBER_INVALID',
            field_errors={'payer_number': ['Enter a valid number.']},
        )
    return name, number


def submit_payment(employee, *, plan, months, method, payer_name, payer_number, transaction_id, expected_amount=None, invoice_id=None, kind=None):
    """The company reports a payment it made outside the system. One pending submission per company, and a
    transaction id counts once per method. The amount saved is the server's quote, or the amount of the renewal
    invoice when `invoice_id` says which bill is being paid (then the plan and length are the invoice's)."""
    if method not in dict(PaymentSubmission.METHOD_CHOICES):
        raise BillingError('Choose how you paid: bKash, Nagad, bank transfer or cash.', code='PAYMENT_METHOD_INVALID', field_errors={'method': ['Choose a valid method.']})
    transaction_id = _clean_transaction_id(transaction_id)
    payer_name, payer_number = _clean_payer(payer_name, payer_number)
    company = employee.company
    if kind not in (None, '', PaymentSubmission.KIND_UPGRADE):
        raise BillingError('Only a plan upgrade can be chosen here.', code='PAYMENT_KIND_INVALID', field_errors={'kind': ['Not a valid kind.']})
    if kind == PaymentSubmission.KIND_UPGRADE and invoice_id:
        raise BillingError('An upgrade is not paid against a renewal invoice.', code='PAYMENT_KIND_INVALID')
    try:
        with transaction.atomic():
            subscription = Subscription.objects.select_for_update().get(pk=get_subscription(company).pk)
            invoice = None
            if invoice_id:
                invoice = _payable_invoice(subscription, invoice_id)
                billed = subscription.next_plan or subscription.plan
                if plan and str(plan).strip().lower() not in (billed.name.lower(), str(billed.id)):
                    raise BillingError('A renewal keeps your current plan. To change the plan, use Change plan.', code='PLAN_CHANGE_NOT_VIA_RENEWAL')
                if months not in (None, '') and parse_months(months) != invoice.months:
                    raise BillingError(f'This invoice is for {invoice.months} months.', code='INVOICE_MONTHS_MISMATCH')
                plan, months = billed.name, invoice.months
            offer = upgrade_quote(company, plan) if kind == PaymentSubmission.KIND_UPGRADE else quote(company, plan, months)
            if invoice:
                if offer['kind'] != PaymentSubmission.KIND_RENEWAL:
                    raise BillingError('This invoice cannot be paid now.', code='INVOICE_NOT_PAYABLE')
                offer['amount'] = invoice.amount            # the bill stands as it was issued
            if expected_amount is not None and Decimal(str(expected_amount)) != offer['amount']:
                raise BillingError(
                    f'The amount changed. It is now {offer["amount"]} {offer["currency"]}. Reload the price and try again.',
                    code='PAYMENT_AMOUNT_MISMATCH',
                )
            if PaymentSubmission.objects.filter(company=company, status=PaymentSubmission.STATUS_PENDING).exists():
                raise BillingError('A payment is already waiting for approval. Wait for the decision before sending another.', code='PAYMENT_ALREADY_PENDING')
            if PaymentSubmission.objects.filter(method=method, transaction_id=transaction_id).exclude(status=PaymentSubmission.STATUS_REJECTED).exists():
                raise BillingError(
                    'This transaction id was already submitted for this payment method.', code='PAYMENT_TRANSACTION_USED',
                    field_errors={'transaction_id': ['This transaction id was already used.']},
                )
            return PaymentSubmission.objects.create(
                company=company, plan_id=offer['plan']['id'], months=offer['months'], amount=offer['amount'],
                currency=offer['currency'], method=method, payer_name=payer_name, payer_number=payer_number,
                transaction_id=transaction_id, kind=offer['kind'], submitted_by=employee, invoice=invoice,
            )
    except IntegrityError:
        # Two requests raced past the checks above; the database constraints decided.
        if PaymentSubmission.objects.filter(company=company, status=PaymentSubmission.STATUS_PENDING).exists():
            raise BillingError('A payment is already waiting for approval. Wait for the decision before sending another.', code='PAYMENT_ALREADY_PENDING') from None
        raise BillingError(
            'This transaction id was already submitted for this payment method.', code='PAYMENT_TRANSACTION_USED',
            field_errors={'transaction_id': ['This transaction id was already used.']},
        ) from None


def _payable_invoice(subscription, invoice_id):
    """The company's own open renewal invoice that no live payment is tied to yet, else INVOICE_NOT_PAYABLE."""
    try:
        wanted = uuid.UUID(str(invoice_id))
    except ValueError:
        wanted = None
    invoice = Invoice.objects.select_for_update().filter(
        pk=wanted, subscription=subscription, kind=Invoice.KIND_RENEWAL, status=Invoice.STATUS_OPEN,
    ).first() if wanted else None
    if invoice is None:
        raise BillingError('This invoice is not open, or it is not your company\'s.', code='INVOICE_NOT_PAYABLE')
    if PaymentSubmission.objects.filter(invoice=invoice).exclude(status=PaymentSubmission.STATUS_REJECTED).exists():
        raise BillingError('A payment is already waiting for this invoice.', code='PAYMENT_ALREADY_PENDING')
    return invoice


def next_invoice_number(on):
    """INV-<year>-<running number>: the next free number of that year."""
    prefix = f'INV-{on.year}-'
    last = Invoice.objects.filter(number__startswith=prefix).order_by('-number').values_list('number', flat=True).first()
    return f'{prefix}{(int(last[len(prefix):]) + 1) if last else 1:05d}'


def _create_paid_invoice(subscription, payment, plan, start, end, today, kind=Invoice.KIND_PAYMENT):
    for _ in range(5):
        try:
            with transaction.atomic():
                return Invoice.objects.create(
                    company=payment.company, subscription=subscription, number=next_invoice_number(today),
                    plan_name=plan.name, period_start=start, period_end=end, amount=payment.amount,
                    currency=payment.currency, status=Invoice.STATUS_PAID, issued_on=today, due_on=today, paid_on=today,
                    payment_method=payment.method, transaction_id=payment.transaction_id,
                    kind=kind, months=payment.months,
                )
        except IntegrityError:
            continue          # the number was taken by another approval at the same moment: take the next one
    raise BillingError('The invoice number could not be reserved. Try again.', code='INVOICE_NUMBER_BUSY')


def _notify_company(payment, kind, title, message):
    from notifications.services import notify
    people = {e.pk: e for e in _billing_recipients(payment.company)}
    if payment.submitted_by_id:
        people.setdefault(payment.submitted_by_id, payment.submitted_by)
    for employee in people.values():
        notify(employee, kind, title, message, '/settings/billing')


@transaction.atomic
def approve_payment(payment, admin_user):
    """Approve a payment: start or extend the subscription and write the paid invoice, once.
    Returns (payment, changed). Approving again changes nothing and returns changed False."""
    payment = PaymentSubmission.objects.select_for_update().select_related('company', 'plan', 'submitted_by').get(pk=payment.pk)
    if payment.status == PaymentSubmission.STATUS_APPROVED:
        return payment, False
    if payment.status == PaymentSubmission.STATUS_REJECTED:
        raise BillingError('This payment was rejected. Ask the company to submit it again.', code='PAYMENT_ALREADY_REJECTED')
    company, plan = payment.company, payment.plan
    subscription = Subscription.objects.select_for_update().select_related('plan', 'next_plan').get(pk=get_subscription(company).pk)
    today = _today(company)
    if payment.kind == PaymentSubmission.KIND_UPGRADE:
        return _approve_upgrade(payment, subscription, admin_user, today)
    # The same rule as the quote, but for today: an old end date that has since been passed starts the new period today.
    kind, start = payment_context(subscription, plan, today)
    end = period_end_for(start, payment.months)
    if payment.invoice_id:
        # The payment settles a bill issued earlier: that same invoice becomes Paid, with the real period.
        invoice = Invoice.objects.select_for_update().get(pk=payment.invoice_id)
        if invoice.status != Invoice.STATUS_OPEN:
            raise BillingError('The invoice of this payment is no longer open.', code='INVOICE_NOT_OPEN')
        invoice.plan_name, invoice.period_start, invoice.period_end = plan.name, start, end
        invoice.months, invoice.amount, invoice.currency = payment.months, payment.amount, payment.currency
        invoice.status, invoice.paid_on = Invoice.STATUS_PAID, today
        invoice.payment_method, invoice.transaction_id = payment.method, payment.transaction_id
        invoice.save()
    else:
        invoice = _create_paid_invoice(subscription, payment, plan, start, end, today)
    if kind == PaymentSubmission.KIND_RENEWAL and effective_state(subscription, today) in (STATE_ACTIVE, STATE_GRACE):
        subscription.current_period_end = end                       # extend: the running period keeps its start
    else:
        subscription.current_period_start, subscription.current_period_end = start, end
        subscription.started_on = start if subscription.status == Subscription.STATUS_PENDING_PAYMENT else subscription.started_on
    if plan.id != subscription.plan_id and start > today:
        # A lower plan bought at renewal: the plan being paid for now keeps running until the new period begins.
        subscription.next_plan, subscription.next_plan_from = plan, start
    else:
        subscription.plan = plan
        subscription.next_plan, subscription.next_plan_from = None, None
    subscription.status = Subscription.STATUS_ACTIVE
    subscription.billing_months = payment.months
    subscription.reminders_sent = []
    subscription.save()
    # A renewal invoice that this payment already covers (for example one issued after an early renewal) is void.
    for stale in Invoice.objects.filter(
        subscription=subscription, kind=Invoice.KIND_RENEWAL, status=Invoice.STATUS_OPEN,
        period_start__lte=subscription.current_period_end,
    ).exclude(pk=invoice.pk):
        stale.status = Invoice.STATUS_VOID
        stale.save(update_fields=['status', 'updated_at'])
    payment.status = PaymentSubmission.STATUS_APPROVED
    payment.reviewed_by, payment.reviewed_at = admin_user, timezone.now()
    payment.period_start, payment.period_end, payment.invoice = start, end, invoice
    payment.save()
    from notifications.models import Notification
    from platform_admin.services import record_payment_action
    record_payment_action(admin_user, payment, 'approve_payment', f'{payment.amount} {payment.currency}, {payment.months} months, until {end}')
    _notify_company(
        payment, Notification.KIND_PAYMENT_APPROVED, 'Payment approved',
        f'Your {plan.name} plan is active until {end}. Invoice {invoice.number} is paid.',
    )
    return payment, True


def _approve_upgrade(payment, subscription, admin_user, today):
    """An approved upgrade switches the plan at once and writes an invoice for the extra amount. The end date and the
    reminders of the running period stay. The amount is what the company paid (the quote of the day it submitted)."""
    company, plan = payment.company, payment.plan
    if effective_state(subscription, today) != STATE_ACTIVE:
        raise BillingError(
            'The paid period of this company has ended, so the upgrade cannot start. Reject this payment with a note '
            'and ask the company to renew first.', code='UPGRADE_PERIOD_ENDED',
        )
    if plan.price_monthly <= subscription.plan.price_monthly:
        raise BillingError(
            f'The company is already on {subscription.plan.name}, which is not lower than {plan.name}. '
            'Reject this payment with a note.', code='UPGRADE_NOT_HIGHER',
        )
    _team_fits(company, plan)
    start, end = today, subscription.current_period_end
    invoice = _create_paid_invoice(subscription, payment, plan, start, end, today, kind=Invoice.KIND_UPGRADE)
    subscription.plan = plan
    subscription.next_plan, subscription.next_plan_from = None, None      # a higher plan cancels a scheduled lower one
    subscription.save()
    _reprice_open_renewal(subscription, plan)
    payment.status = PaymentSubmission.STATUS_APPROVED
    payment.reviewed_by, payment.reviewed_at = admin_user, timezone.now()
    payment.period_start, payment.period_end, payment.invoice = start, end, invoice
    payment.save()
    from notifications.models import Notification
    from platform_admin.services import record_payment_action
    record_payment_action(admin_user, payment, 'approve_payment', f'upgrade to {plan.name}: {payment.amount} {payment.currency}, until {end}')
    _notify_company(
        payment, Notification.KIND_PAYMENT_APPROVED, 'Plan upgraded',
        f'Your company is now on the {plan.name} plan until {end}. Invoice {invoice.number} is paid.',
    )
    return payment, True


@transaction.atomic
def reject_payment(payment, admin_user, note):
    """Reject a pending payment with a reason the company will read. Rejecting again changes nothing."""
    note = str(note or '').strip()
    payment = PaymentSubmission.objects.select_for_update().select_related('company', 'submitted_by').get(pk=payment.pk)
    if payment.status == PaymentSubmission.STATUS_REJECTED:
        return payment, False
    if payment.status == PaymentSubmission.STATUS_APPROVED:
        raise BillingError('This payment was already approved.', code='PAYMENT_ALREADY_APPROVED')
    if not note:
        raise BillingError('Write why the payment is rejected. The company will read it.', code='REJECTION_NOTE_REQUIRED', field_errors={'note': ['This field is required.']})
    payment.status = PaymentSubmission.STATUS_REJECTED
    payment.reviewed_by, payment.reviewed_at, payment.review_note = admin_user, timezone.now(), note[:500]
    payment.save()
    from notifications.models import Notification
    from platform_admin.services import record_payment_action
    record_payment_action(admin_user, payment, 'reject_payment', note)
    _notify_company(payment, Notification.KIND_PAYMENT_REJECTED, 'Payment rejected', f'Your payment was not accepted: {note[:300]}')
    return payment, True


def payment_instructions():
    """How to pay outside the system, from the server settings (the payment page shows exactly this)."""
    from django.conf import settings
    allowed = dict(PaymentSubmission.METHOD_CHOICES)
    methods = [
        {'method': item['method'], 'label': item.get('label') or allowed[item['method']], 'instructions': item.get('instructions', '')}
        for item in getattr(settings, 'PAYMENT_INSTRUCTIONS', []) if item.get('method') in allowed
    ]
    return {'methods': methods, 'note': getattr(settings, 'PAYMENT_NOTE', '')}


# ---------- Platform Admin: every company's subscription (ST-148) ----------

EXPIRING_DAYS = 7          # "expiring soon" = this many days left or fewer


def _zone_today(tz_name, now, cache):
    """Today's date in one time zone; each zone is worked out once per request."""
    if tz_name not in cache:
        try:
            zone = ZoneInfo(tz_name) if tz_name else timezone.get_default_timezone()
        except (ZoneInfoNotFoundError, ValueError):
            zone = timezone.get_default_timezone()
        cache[tz_name] = now.astimezone(zone).date()
    return cache[tz_name]


def admin_subscription_rows(flt='', query=''):
    """One row per company with its plan, state, end date and days left (the company's own today),
    soonest-ending first. A company waiting for its first payment has no days left and goes last.
    flt: 'expiring' (7 days or fewer, still working) or 'restricted' (expired or waiting for payment)."""
    from attendance.services import _now
    now, cache = _now(), {}
    subscriptions = Subscription.objects.select_related('company', 'plan', 'company__settings')
    if query:
        subscriptions = subscriptions.filter(
            models.Q(company__name__icontains=query) | models.Q(company__subdomain__icontains=query),
        )
    rows = []
    for sub in subscriptions:
        company = sub.company
        try:
            tz_name = company.settings.timezone
        except ObjectDoesNotExist:
            tz_name = ''
        today = _zone_today(tz_name, now, cache)
        state = effective_state(sub, today)
        left = None if state in (STATE_PENDING_PAYMENT, STATE_CANCELLED) else (sub.current_period_end - today).days
        restricted = state in (STATE_PENDING_PAYMENT, STATE_EXPIRED)
        if flt == 'restricted' and not restricted:
            continue
        if flt == 'expiring' and not (state in (STATE_ACTIVE, STATE_GRACE) and left <= EXPIRING_DAYS):
            continue
        rows.append({
            'id': sub.id, 'company': company.id, 'company_name': company.name, 'company_subdomain': company.subdomain,
            'company_suspended': not company.is_active, 'plan_name': sub.plan.name, 'status': state,
            'restricted': restricted, 'period_start': sub.current_period_start, 'period_end': sub.current_period_end,
            'billing_months': sub.billing_months, 'days_left': left,
        })
    rows.sort(key=lambda r: (r['days_left'] is None, r['days_left'] if r['days_left'] is not None else 0, r['company_name'].lower()))
    return rows


def pending_payment_count():
    return PaymentSubmission.objects.filter(status=PaymentSubmission.STATUS_PENDING).count()
