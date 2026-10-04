"""Seeds the manage_approval_chains Permission (ST-112)."""
from django.db import migrations


def seed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.get_or_create(
        codename='manage_approval_chains',
        defaults={'name': 'Manage Approval Chains', 'module': 'approvals'},
    )


def unseed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='manage_approval_chains').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0005_employeerole'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
