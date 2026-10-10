from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = (
        'Creates a Platform Admin login (company-less, no Employee record). '
        'Platform Admins cannot be created through the website or the API.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', help='Leave out to be asked (not shown on screen).')

    def handle(self, *args, email, password=None, **options):
        email = User.objects.normalize_email(email)
        if User.objects.filter(email=email).exists():
            raise CommandError(f'{email} already exists.')
        password = password or getpass('Password: ')
        if len(password) < 8:
            raise CommandError('Password must be at least 8 characters.')
        User.objects.create_user(email=email, password=password, is_platform_admin=True)
        self.stdout.write(self.style.SUCCESS(f'Platform Admin {email} created.'))
