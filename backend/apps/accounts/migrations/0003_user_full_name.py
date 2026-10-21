"""ST-140: the person's real name on the User (blank for old rows)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_is_platform_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='full_name',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
    ]
