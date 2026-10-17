"""Seeds view_audit_log (ST-135): who may read the company's Audit Log. The system Admin role (the CEO) receives it automatically."""
from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.get_or_create(
        codename='view_audit_log',
        defaults={'name': 'View Audit Log', 'module': 'audit_log'},
    )


def unseed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.filter(codename='view_audit_log').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0011_seed_manage_leave_types'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
