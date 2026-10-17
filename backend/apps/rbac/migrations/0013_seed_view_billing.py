"""Seeds view_billing (ST-136): who may see the company's plan, employee usage and invoices. The CEO role receives it automatically."""
from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.get_or_create(
        codename='view_billing',
        defaults={'name': 'View Billing', 'module': 'billing'},
    )


def unseed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.filter(codename='view_billing').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0012_seed_view_audit_log'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
