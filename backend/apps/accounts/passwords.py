"""Temporary passwords and the change-password rules (ST-142)."""
import secrets

from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# No 0/O, 1/l/I: a password read out loud or typed from a screen must not be ambiguous.
_ALPHABET = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
TEMPORARY_PASSWORD_LENGTH = 12


def make_temporary_password():
    """A random one-time password that satisfies the password rules (letters and digits, 12 characters)."""
    while True:
        candidate = ''.join(secrets.choice(_ALPHABET) for _ in range(TEMPORARY_PASSWORD_LENGTH))
        if any(c.isdigit() for c in candidate) and any(c.islower() for c in candidate) and any(c.isupper() for c in candidate):
            return candidate


def end_other_sessions(user, keep_refresh_token=None):
    """
    Blacklists every refresh token of the user except the one the caller is using now
    (so the person stays logged in here and is logged out everywhere else).
    Returns how many tokens were ended.
    """
    keep_jti = None
    if keep_refresh_token:
        try:
            token = RefreshToken(keep_refresh_token)
            if str(token.get('user_id')) == str(user.pk):
                keep_jti = token['jti']
        except TokenError:
            keep_jti = None
    ended = 0
    for outstanding in OutstandingToken.objects.filter(user=user):
        if keep_jti and outstanding.jti == keep_jti:
            continue
        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        ended += int(created)
    return ended


def check_new_password(user, new_password):
    """Applies the project's password rules (settings.AUTH_PASSWORD_VALIDATORS). Raises Django's ValidationError."""
    validate_password(new_password, user=user)
