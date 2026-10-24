import datetime

from billing import services
from billing.models import Invoice, PaymentSubmission

ORDER = 80


def seed(ctx):
    """The demo company is on Basic (10 of 10 seats used, so adding an employee shows the limit). Three paid months, this month open."""
    subscription = services.get_subscription(ctx.company)
    today = ctx.today
    # The demo company is always active with a long period, so re-running the seeder later never leaves it restricted.
    if subscription.status != subscription.STATUS_ACTIVE or subscription.current_period_end < today + datetime.timedelta(days=60):
        subscription.status = subscription.STATUS_ACTIVE
        services.set_period(subscription, today, services.DEFAULT_MONTHS)
        subscription.save()
    months = []
    year, month = today.year, today.month
    for _ in range(4):
        months.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    for index, (year, month) in enumerate(reversed(months)):
        invoice, created = services.generate_invoice(subscription, year, month)
        ctx.note('invoices', created)
        if index < 3 and invoice.status == Invoice.STATUS_OPEN:
            services.mark_paid(invoice, on=invoice.issued_on)

    # One approved payment, so the Payments list and the payment routes have something to show.
    price = services.price_for(subscription.plan, services.DEFAULT_MONTHS)
    _, made = PaymentSubmission.objects.get_or_create(
        method=PaymentSubmission.METHOD_BKASH, transaction_id='DEMO0000AB',
        defaults={
            'company': ctx.company, 'plan': subscription.plan, 'months': services.DEFAULT_MONTHS,
            'amount': price['amount'], 'currency': subscription.plan.currency, 'payer_name': 'Demo Owner',
            'payer_number': '01700000000', 'kind': PaymentSubmission.KIND_NEW, 'status': PaymentSubmission.STATUS_APPROVED,
            'reviewed_at': subscription.created_at, 'review_note': '',
            'period_start': subscription.current_period_start, 'period_end': subscription.current_period_end,
        },
    )
    ctx.note('payments', made)
