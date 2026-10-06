from django.db import migrations


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')

    permissions = [
        ('view_attendance', 'View Attendance', 'attendance'),
        ('manage_attendance', 'Manage Attendance', 'attendance'),
    ]

    for codename, name, module in permissions:
        Permission.objects.get_or_create(
            codename=codename,
            defaults={
                'name': name,
                'module': module,
            },
        )


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')

    Permission.objects.filter(
        codename__in=[
            'view_attendance',
            'manage_attendance',
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0007_seed_create_task'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]