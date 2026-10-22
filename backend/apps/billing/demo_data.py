import datetime

from billing import services
from billing.models import Invoice

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
