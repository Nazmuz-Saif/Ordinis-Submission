"""
Data migration: Seeds the initial set of system-wide permissions.
These are the permission codenames that views already reference
(manage_departments, manage_employees, etc.).
"""
from django.db import migrations


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')

    initial_permissions = [
        # (codename, human-readable name, module)
        ('manage_departments', 'Manage Departments', 'organization'),
        ('manage_designations', 'Manage Designations', 'organization'),
        ('manage_employees', 'Manage Employees', 'organization'),
        ('manage_roles', 'Manage Roles', 'roles'),
        ('assign_roles', 'Assign Roles', 'roles'),
    ]

    for codename, name, module in initial_permissions:
        Permission.objects.get_or_create(
            codename=codename,
            defaults={'name': name, 'module': module},
        )


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename__in=[
        'manage_departments', 'manage_designations',
        'manage_employees', 'manage_roles', 'assign_roles',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]
