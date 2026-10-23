import calendar
import datetime
from decimal import Decimal

import re
import uuid

from django.db import IntegrityError, transaction
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
MIN_MONTHS, MAX_MONTHS = 1, 36  # how many months one payment can buy
FREE_MONTHS_PER_YEAR = 2        # every full 12 months costs 10: 12 months = price of 10, 24 = 20, 36 = 30
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
        if plan.id != subscription.plan_id:
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


def submit_payment(employee, *, plan, months, method, payer_name, payer_number, transaction_id, expected_amount=None):
    """The company reports a payment it made outside the system. One pending submission per company, and a
    transaction id counts once per method. The amount saved is the server's quote."""
    if method not in dict(PaymentSubmission.METHOD_CHOICES):
        raise BillingError('Choose how you paid: bKash, Nagad, bank transfer or cash.', code='PAYMENT_METHOD_INVALID', field_errors={'method': ['Choose a valid method.']})
    transaction_id = _clean_transaction_id(transaction_id)
    payer_name, payer_number = _clean_payer(payer_name, payer_number)
    company = employee.company
    try:
        with transaction.atomic():
            subscription = Subscription.objects.select_for_update().get(pk=get_subscription(company).pk)
            offer = quote(company, plan, months)
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
                transaction_id=transaction_id, kind=offer['kind'], submitted_by=employee,
            )
    except IntegrityError:
        # Two requests raced past the checks above; the database constraints decided.
        if PaymentSubmission.objects.filter(company=company, status=PaymentSubmission.STATUS_PENDING).exists():
            raise BillingError('A payment is already waiting for approval. Wait for the decision before sending another.', code='PAYMENT_ALREADY_PENDING') from None
        raise BillingError(
            'This transaction id was already submitted for this payment method.', code='PAYMENT_TRANSACTION_USED',
            field_errors={'transaction_id': ['This transaction id was already used.']},
        ) from None


def next_invoice_number(on):
    """INV-<year>-<running number>: the next free number of that year."""
    prefix = f'INV-{on.year}-'
    last = Invoice.objects.filter(number__startswith=prefix).order_by('-number').values_list('number', flat=True).first()
    return f'{prefix}{(int(last[len(prefix):]) + 1) if last else 1:05d}'


def _create_paid_invoice(subscription, payment, plan, start, end, today):
    for _ in range(5):
        try:
            with transaction.atomic():
                return Invoice.objects.create(
                    company=payment.company, subscription=subscription, number=next_invoice_number(today),
                    plan_name=plan.name, period_start=start, period_end=end, amount=payment.amount,
                    currency=payment.currency, status=Invoice.STATUS_PAID, issued_on=today, due_on=today, paid_on=today,
                    payment_method=payment.method, transaction_id=payment.transaction_id,
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
    if payment.kind == PaymentSubmission.KIND_UPGRADE:
        raise BillingError('Upgrade payments are not handled here yet.', code='PAYMENT_KIND_UNSUPPORTED')
    company, plan = payment.company, payment.plan
    subscription = Subscription.objects.select_for_update().select_related('plan').get(pk=get_subscription(company).pk)
    today = _today(company)
    # The same rule as the quote, but for today: an old end date that has since been passed starts the new period today.
    kind, start = payment_context(subscription, plan, today)
    end = period_end_for(start, payment.months)
    invoice = _create_paid_invoice(subscription, payment, plan, start, end, today)
    if kind == PaymentSubmission.KIND_RENEWAL and effective_state(subscription, today) in (STATE_ACTIVE, STATE_GRACE):
        subscription.current_period_end = end                       # extend: the running period keeps its start
    else:
        subscription.current_period_start, subscription.current_period_end = start, end
        subscription.started_on = start if subscription.status == Subscription.STATUS_PENDING_PAYMENT else subscription.started_on
    subscription.plan = plan
    subscription.status = Subscription.STATUS_ACTIVE
    subscription.billing_months = payment.months
    subscription.reminders_sent = []
    subscription.save()
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
