from django.db import migrations


def seed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.get_or_create(
        codename='finance',
        defaults={
            'name': 'Finance',
            'module': 'payroll',
        },
    )


def unseed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='finance').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0007_seed_create_task'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]