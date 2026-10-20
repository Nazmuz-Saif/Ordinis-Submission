"""Seeds view_analytics (ST-134): who may open the Analytics page. The CEO role receives it automatically."""
from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.get_or_create(
        codename='view_analytics',
        defaults={'name': 'View Analytics', 'module': 'analytics'},
    )


def unseed(apps, schema_editor):
    apps.get_model('roles', 'Permission').objects.filter(codename='view_analytics').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0013_seed_view_billing'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
