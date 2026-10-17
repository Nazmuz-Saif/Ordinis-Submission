"""
Who is acting right now? The middleware stores the current request here; signals read it.
A management command (the demo-data loader) can act as a named system instead:  with audit_context('System (demo data)'): ...
Outside both (a plain script, a test calling the ORM) nothing is logged: the log records actions through the API.
"""
import contextvars
from contextlib import contextmanager

_request = contextvars.ContextVar('audit_request', default=None)
_system = contextvars.ContextVar('audit_system', default=None)


def set_request(request):
    return _request.set(request)


def reset_request(token):
    _request.reset(token)


@contextmanager
def audit_context(system_label):
    token = _system.set(system_label)
    try:
        yield
    finally:
        _system.reset(token)


def current():
    """(user, ip, system_label, active). `active` is False when nothing should be logged."""
    request = _request.get()
    label = _system.get()
    if request is not None:
        user = getattr(request, 'user', None)
        if user is not None and getattr(user, 'is_authenticated', False):
            return user, client_ip(request), None, True
    if label:
        return None, None, label, True
    return None, None, None, False


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None
