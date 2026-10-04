"""Seeds the create_task Permission (ST-116)."""
from django.db import migrations


def seed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.get_or_create(
        codename='create_task',
        defaults={'name': 'Create Tasks', 'module': 'tasks'},
    )


def unseed(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='create_task').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0006_seed_manage_approval_chains'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
