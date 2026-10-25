"""
The Platform Admin's detail page of one company (ST-152).

It answers "who is this company and is it in good standing?" with contacts, counts and OUR OWN records only.
It never contains an employee name (the owner, the one contact the company gave us at registration, is the only
person), a task, an attendance row or a salary: Break-Glass stays the only way into that data.
"""
from django.db.models import Count, Q, Sum
from django.utils import timezone

from billing import services as billing_services
from billing.models import Invoice, PaymentSubmission, Subscription
from organization.models import Employee

from .models import PlatformActionLog, SupportAccessRequest, SupportTicket

RECENT_ACTIONS = 10
STATUS_ACTIONS = ('suspend', 'activate')


def _owner(company):
    """The company's CEO: the holder of its system CEO role, the earliest one if there are several."""
    employee = (
        Employee.objects.filter(company=company, employee_roles__role__is_system_default=True, employee_roles__role__name='CEO')
        .select_related('user').order_by('created_at', 'id').first()
    )
    if employee is None:
        return None
    return {'full_name': employee.user.full_name, 'email': employee.user.email, 'phone': employee.phone}


def _action(row):
    return {
        'id': str(row.id), 'action': row.action, 'note': row.note, 'created_at': row.created_at,
        'actor_name': row.actor.full_name or row.actor.email,
    }


def _subscription(company):
    subscription = Subscription.objects.filter(company=company).select_related('plan', 'next_plan').first()
    if subscription is None:
        return None
    plan = subscription.plan
    return {
        'plan': {
            'name': plan.name, 'price_monthly': plan.price_monthly, 'currency': plan.currency,
            'max_employees': plan.max_employees, 'unlimited': plan.max_employees is None,
        },
        'next_plan': subscription.next_plan.name if subscription.next_plan_id else None,
        'status': billing_services.effective_state(subscription),
        'started_on': subscription.started_on,
        'period_start': subscription.current_period_start,
        'period_end': subscription.current_period_end,
        'days_left': billing_services.days_left(subscription),
        'billing_months': subscription.billing_months,
    }


def _invoices(company):
    paid = Q(status=Invoice.STATUS_PAID)
    opened = Q(status=Invoice.STATUS_OPEN)
    totals = Invoice.objects.filter(company=company).aggregate(
        total=Count('id'), open=Count('id', filter=opened), paid=Count('id', filter=paid),
        void=Count('id', filter=Q(status=Invoice.STATUS_VOID)),
        open_amount=Sum('amount', filter=opened), paid_amount=Sum('amount', filter=paid),
    )
    totals['open_amount'] = totals['open_amount'] or 0
    totals['paid_amount'] = totals['paid_amount'] or 0
    return totals


def _payments(company):
    approved = Q(status=PaymentSubmission.STATUS_APPROVED)
    totals = PaymentSubmission.objects.filter(company=company).aggregate(
        total=Count('id'), pending=Count('id', filter=Q(status=PaymentSubmission.STATUS_PENDING)), approved=Count('id', filter=approved),
        rejected=Count('id', filter=Q(status=PaymentSubmission.STATUS_REJECTED)), approved_amount=Sum('amount', filter=approved),
    )
    totals['approved_amount'] = totals['approved_amount'] or 0
    last = PaymentSubmission.objects.filter(company=company, status=PaymentSubmission.STATUS_APPROVED).order_by('-reviewed_at', '-created_at').first()
    totals['last_approved_at'] = (last.reviewed_at or last.created_at) if last else None
    return totals


def company_detail(company):
    now = timezone.now()
    tickets = SupportTicket.objects.filter(company=company).aggregate(
        total=Count('id'), open=Count('id', filter=Q(status=SupportTicket.STATUS_OPEN)),
    )
    requests = SupportAccessRequest.objects.filter(company=company).aggregate(
        total=Count('id'), pending=Count('id', filter=Q(status=SupportAccessRequest.STATUS_PENDING)),
        active=Count('id', filter=Q(status=SupportAccessRequest.STATUS_APPROVED, expires_at__gt=now)),
    )
    actions = PlatformActionLog.objects.filter(company=company).select_related('actor').order_by('-created_at', '-id')
    last_status = actions.filter(action__in=STATUS_ACTIONS).first()
    return {
        'id': str(company.id),
        'name': company.name,
        'subdomain': company.subdomain,
        'industry': company.industry,
        'registered_on': company.created_at,
        'is_active': company.is_active,
        'last_status_action': _action(last_status) if last_status else None,
        'owner': _owner(company),
        'subscription': _subscription(company),
        'size': billing_services.usage(company),
        'invoices': _invoices(company),
        'payments': _payments(company),
        'tickets': tickets,
        'access_requests': requests,
        'recent_actions': [_action(row) for row in actions[:RECENT_ACTIONS]],
    }
