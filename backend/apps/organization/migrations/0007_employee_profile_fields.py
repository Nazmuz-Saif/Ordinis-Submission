"""ST-140: profile details on Employee (all blank or empty for old rows)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0006_employee_code_unique_per_company'),
    ]

    operations = [
        migrations.AddField(model_name='employee', name='phone', field=models.CharField(blank=True, default='', max_length=30)),
        migrations.AddField(model_name='employee', name='address', field=models.CharField(blank=True, default='', max_length=255)),
        migrations.AddField(model_name='employee', name='emergency_contact_name', field=models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField(model_name='employee', name='emergency_contact_phone', field=models.CharField(blank=True, default='', max_length=30)),
        migrations.AddField(model_name='employee', name='joined_on', field=models.DateField(blank=True, null=True)),
    ]
