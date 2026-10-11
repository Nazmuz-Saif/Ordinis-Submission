"""Seeds manage_leave_types (ST-128): who may create, change and delete the company's Leave Types.
The system Admin role (the CEO) receives it automatically."""
from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.get_or_create(
        codename='manage_leave_types',
        defaults={'name': 'Manage Leave Types', 'module': 'attendance'},
    )


def unseed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.filter(codename='manage_leave_types').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0010_seed_approve_support_access'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
