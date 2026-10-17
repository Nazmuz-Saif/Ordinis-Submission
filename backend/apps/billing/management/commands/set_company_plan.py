from django.core.management.base import BaseCommand, CommandError

from billing import services
from tenants.models import Company


class Command(BaseCommand):
    help = 'Moves a company to a plan (there is no payment step yet). Example: python manage.py set_company_plan demo-acme Professional'

    def add_arguments(self, parser):
        parser.add_argument('subdomain')
        parser.add_argument('plan')

    def handle(self, *args, **opts):
        company = Company.objects.filter(subdomain=opts['subdomain']).first()
        if company is None:
            raise CommandError(f'No company with subdomain "{opts["subdomain"]}".')
        services.seed_plans()
        try:
            subscription = services.change_plan(company, opts['plan'])
        except services.BillingError as exc:
            raise CommandError(exc.message)
        self.stdout.write(f'{company.name} is now on the {subscription.plan.name} plan.')
