import datetime

from django.core.management.base import BaseCommand

from billing import services
from billing.models import Subscription


class Command(BaseCommand):
    help = 'Creates the invoice of one month (default: this month) for every active subscription. Safe to run twice.'

    def add_arguments(self, parser):
        parser.add_argument('--month', help='YYYY-MM (default: the current month)')

    def handle(self, *args, **opts):
        today = datetime.date.today()
        year, month = (int(p) for p in opts['month'].split('-')) if opts['month'] else (today.year, today.month)
        made = 0
        for subscription in Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).select_related('plan', 'company'):
            _, created = services.generate_invoice(subscription, year, month)
            made += created
        self.stdout.write(f'{made} new invoice(s) for {year}-{month:02d}.')
