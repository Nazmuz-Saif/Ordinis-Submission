"""ST-138: a plain-language description on every Permission. The text itself comes from rbac/catalog.py after migrate."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0014_seed_view_analytics'),
    ]

    operations = [
        migrations.AddField(
            model_name='permission',
            name='description',
            field=models.CharField(blank=True, default='', help_text='Plain-language explanation of what this Permission lets a person do.', max_length=500),
        ),
    ]
