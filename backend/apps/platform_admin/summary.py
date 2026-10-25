"""
The Platform Admin home (ST-153): the health of the whole platform on one screen.

Every number is read from OUR OWN records (companies, subscriptions, invoices, payments, tickets, access requests),
never from a company's operational data. The number of database queries is fixed: it does not grow with the number
of companies.
"""
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from attendance.services import _now
from billing import services as billing_services
from billing.models import Invoice, PaymentSubmission
from billing.services import EXPIRING_DAYS, STATE_ACTIVE, STATE_EXPIRED, STATE_GRACE, STATE_PENDING_PAYMENT
from tenants.models import Company

from .models import SupportAccessRequest, SupportTicket

MONTHS_SHOWN = 6


def _month_starts(today):
    """The first day of each of the last 6 months, oldest first, this month last."""
    year, month, starts = today.year, today.month, []
    for _ in range(MONTHS_SHOWN):
        starts.append(today.replace(year=year, month=month, day=1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return starts[::-1]


def _company_states():
    """(total, active, restricted, suspended, ending soon) with each company's own 'today', from ONE query."""
    now, cache = _now(), {}
    counts = {'total': 0, 'active': 0, 'restricted': 0, 'suspended': 0, 'ending': 0}
    for company in Company.objects.select_related('subscription', 'settings'):
        counts['total'] += 1
        subscription = getattr(company, 'subscription', None)
        if subscription is not None:
            try:
                zone_name = company.settings.timezone
            except Exception:
                zone_name = ''
            today = billing_services._zone_today(zone_name, now, cache)
            state = billing_services.effective_state(subscription, today)
            left = (subscription.current_period_end - today).days
            if state in (STATE_ACTIVE, STATE_GRACE) and left <= EXPIRING_DAYS:
                counts['ending'] += 1
        else:
            state = STATE_ACTIVE
        if not company.is_active:
            counts['suspended'] += 1
        elif state in (STATE_PENDING_PAYMENT, STATE_EXPIRED):
            counts['restricted'] += 1
        else:
            counts['active'] += 1
    return counts


def platform_summary():
    today = timezone.localdate()
    months = _month_starts(today)
    states = _company_states()

    paid, opened = Q(status=Invoice.STATUS_PAID), Q(status=Invoice.STATUS_OPEN)
    money = Invoice.objects.aggregate(
        all_time=Sum('amount', filter=paid),
        this_month=Sum('amount', filter=paid & Q(paid_on__gte=months[-1])),
        due=Sum('amount', filter=opened), due_count=Count('id', filter=opened),
    )
    by_month = {
        row['month'].date() if hasattr(row['month'], 'date') else row['month']: row['total']
        for row in Invoice.objects.filter(paid, paid_on__gte=months[0])
        .annotate(month=TruncMonth('paid_on')).values('month').annotate(total=Sum('amount')).order_by('month')
    }

    pending_payments = PaymentSubmission.objects.filter(status=PaymentSubmission.STATUS_PENDING).count()
    open_tickets = SupportTicket.objects.filter(status=SupportTicket.STATUS_OPEN).count()
    pending_requests = SupportAccessRequest.objects.filter(status=SupportAccessRequest.STATUS_PENDING).count()

    return {
        'companies': {key: states[key] for key in ('total', 'active', 'restricted', 'suspended')},
        'subscriptions_ending': states['ending'],
        'revenue': {'this_month': money['this_month'] or 0, 'all_time': money['all_time'] or 0, 'currency': 'BDT'},
        'due': {'amount': money['due'] or 0, 'count': money['due_count'] or 0},
        'pending_payments': pending_payments,
        'open_tickets': open_tickets,
        'pending_access_requests': pending_requests,
        'revenue_by_month': [{'month': m.isoformat(), 'revenue': by_month.get(m, 0)} for m in months],
        'attention': [
            {'key': 'pending_payments', 'count': pending_payments},
            {'key': 'subscriptions_ending', 'count': states['ending']},
            {'key': 'open_tickets', 'count': open_tickets},
            {'key': 'pending_access_requests', 'count': pending_requests},
        ],
    }
