import datetime

from django.core.management.base import BaseCommand, CommandError

from analytics import services
from tenants.models import Company


class Command(BaseCommand):
    help = 'Stores the health snapshot of every active company for one day (default: today in the company time zone). Safe to run twice.'

    def add_arguments(self, parser):
        parser.add_argument('--date', help='YYYY-MM-DD (default: today)')
        parser.add_argument('--company', help='only this company (its subdomain)')

    def handle(self, *args, **opts):
        day = None
        if opts['date']:
            try:
                day = datetime.date.fromisoformat(opts['date'])
            except ValueError:
                raise CommandError('--date must look like 2026-10-19')
        companies = Company.objects.filter(is_active=True)
        if opts['company']:
            companies = companies.filter(subdomain=opts['company'])
            if not companies.exists():
                raise CommandError(f'No active company with the subdomain "{opts["company"]}".')
        made = refreshed = 0
        for company in companies:
            _snapshot, created = services.take_snapshot(company, day)
            made += created
            refreshed += not created
        self.stdout.write(f'{made} new snapshot(s), {refreshed} refreshed.')
