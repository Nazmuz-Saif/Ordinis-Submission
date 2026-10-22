from contextlib import nullcontext

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from accounts.serializers import CompanyRegisterSerializer
from core import demo
from tenants.models import Company


def _wipe():
    """Remove the demo company and its users. Nothing else is touched."""
    company = Company.objects.filter(subdomain=demo.SUBDOMAIN).first()
    if company is None:
        return False
    with transaction.atomic():
        for _name, wipe in demo.discover_wipers():
            wipe(company)
        User.objects.filter(company=company).delete()
        company.delete()
    return True


def _ensure_company():
    company = Company.objects.filter(subdomain=demo.SUBDOMAIN).first()
    if company:
        return company
    serializer = CompanyRegisterSerializer(data={
        'company_name': demo.COMPANY_NAME, 'subdomain': demo.SUBDOMAIN, 'industry': demo.INDUSTRY,
        'ceo_full_name': demo.name('ceo'), 'ceo_email': demo.email('ceo'), 'ceo_password': demo.PASSWORD,
    })
    serializer.is_valid(raise_exception=True)
    return serializer.save()['company']


class Command(BaseCommand):
    help = (
        'Fills the system with a realistic demo company (Acme Technologies Ltd.). Safe to run twice: nothing is '
        'duplicated. --reset removes the demo company and builds it again; --delete only removes it. '
        'Other companies are never touched. Refuses to run with production settings.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Remove the demo company, then build it again.')
        parser.add_argument('--delete', action='store_true', help='Only remove the demo company.')

    def handle(self, *args, **opts):
        if 'production' in settings.SETTINGS_MODULE.lower():
            raise CommandError('Refusing to run: demo data is for development only, and this uses production settings.')
        if opts['reset'] and opts['delete']:
            raise CommandError('Use --reset or --delete, not both.')

        if opts['reset'] or opts['delete']:
            removed = _wipe()
            self.stdout.write('Removed the demo company.' if removed else 'There was no demo company to remove.')
            if opts['delete']:
                return

        try:
            from audit_log.context import audit_context
            acting = audit_context('System (demo data)')   # the load shows in the Audit Log as the system, not as a person
        except ImportError:
            acting = nullcontext()
        with transaction.atomic(), acting:
            ctx = demo.DemoContext(_ensure_company())
            for order, app_name, seed in demo.discover_seeders():
                seed(ctx)
                self.stdout.write(f'  {order:>3}  {app_name}')

        total = sum(ctx.created.values())
        self.stdout.write(self.style.SUCCESS(
            f'Demo company "{demo.COMPANY_NAME}" is ready ({total} new records this run).' if total
            else f'Demo company "{demo.COMPANY_NAME}" is ready (nothing new: it was already complete).'
        ))
        for label, count in sorted(ctx.created.items()):
            self.stdout.write(f'    {label}: +{count}')
        self.stdout.write(f'\nLog in with password {demo.PASSWORD}:')
        for role, local in demo.LOGINS + [demo.PLATFORM_LOGIN]:
            self.stdout.write(f'    {role:<14} {demo.email(local)}')
