from django.core.management.base import BaseCommand

from billing import services


class Command(BaseCommand):
    help = (
        'Daily job: sends the 7, 3 and 1 day billing reminders and moves a subscription to expired '
        f'{services.GRACE_DAYS} days after its end date. Safe to run twice.'
    )

    def handle(self, *args, **opts):
        result = services.process_subscriptions()
        self.stdout.write(
            f"{result['checked']} subscription(s) checked, {result['reminded']} reminder(s) sent, "
            f"{result['expired']} expired, {result['errors']} error(s)."
        )
