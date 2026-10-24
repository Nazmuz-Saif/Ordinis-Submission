import datetime

from django.db import migrations, models


def give_old_rows_a_period(apps, schema_editor):
    """Old subscriptions had no end date. They get a long one, so no existing company becomes restricted."""
    Subscription = apps.get_model('billing', 'Subscription')
    far = datetime.date.today() + datetime.timedelta(days=3650)
    for sub in Subscription.objects.all():
        sub.current_period_start = sub.started_on
        sub.current_period_end = far
        sub.billing_months = 120
        sub.save(update_fields=['current_period_start', 'current_period_end', 'billing_months'])


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_seed_plans_and_subscriptions'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription', name='current_period_start', field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='subscription', name='current_period_end', field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='subscription', name='billing_months',
            field=models.PositiveSmallIntegerField(default=12),
        ),
        migrations.AddField(
            model_name='subscription', name='reminders_sent',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(give_old_rows_a_period, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='subscription', name='current_period_start', field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='subscription', name='current_period_end', field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='subscription', name='status',
            field=models.CharField(
                choices=[('pending_payment', 'Pending payment'), ('active', 'Active'),
                         ('expired', 'Expired'), ('cancelled', 'Cancelled')],
                default='active', max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name='subscription',
            constraint=models.CheckConstraint(
                condition=models.Q(('current_period_end__gte', models.F('current_period_start'))),
                name='subscription_period_end_not_before_start',
            ),
        ),
    ]
