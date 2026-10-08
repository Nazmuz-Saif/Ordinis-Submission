"""Seeds the manage_company_settings Permission (ST-121).

Before this, any employee could change or delete their company's currency, timezone
and language. Now only holders of this Permission (the system Admin role has it) can edit.
"""
from django.db import migrations


def seed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.get_or_create(
        codename='manage_company_settings',
        defaults={'name': 'Manage Company Settings', 'module': 'tenants'},
    )


def unseed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='manage_company_settings').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0008_seed_manage_finance'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
