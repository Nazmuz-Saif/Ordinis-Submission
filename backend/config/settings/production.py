from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

# Production must never run on the development fallback key.
if not os.environ.get('DJANGO_SECRET_KEY'):
    raise ImproperlyConfigured('Set the DJANGO_SECRET_KEY environment variable for production.')
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS (comma separated) for production.')
