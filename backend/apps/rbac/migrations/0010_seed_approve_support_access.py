"""Seeds approve_support_access (ST-123): lets a company's CEO decide Break-Glass requests
and read the access log. The system Admin role (the CEO) receives it automatically."""
from django.db import migrations


def seed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.get_or_create(
        codename='approve_support_access',
        defaults={'name': 'Approve Support Access', 'module': 'platform_admin'},
    )


def unseed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.filter(codename='approve_support_access').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0009_seed_manage_company_settings'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
