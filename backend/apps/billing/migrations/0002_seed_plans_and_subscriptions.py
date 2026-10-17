"""Seeds Basic (10 employees), Professional (50) and Enterprise (unlimited), and puts every company that already exists on Basic."""
import datetime
from decimal import Decimal

from django.db import migrations

PLANS = [('Basic', 10, Decimal('1500.00')), ('Professional', 50, Decimal('5000.00')), ('Enterprise', None, Decimal('15000.00'))]


def seed(apps, schema_editor):
    Plan = apps.get_model('billing', 'SubscriptionPlan')
    Subscription = apps.get_model('billing', 'Subscription')
    Company = apps.get_model('tenants', 'Company')
    for name, limit, price in PLANS:
        Plan.objects.get_or_create(name=name, defaults={'max_employees': limit, 'price_monthly': price})
    basic = Plan.objects.get(name='Basic')
    for company in Company.objects.all():
        Subscription.objects.get_or_create(company=company, defaults={'plan': basic, 'started_on': datetime.date.today()})


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
