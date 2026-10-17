import re

from . import context
from .services import safe_record

WRITE = {'POST', 'PUT', 'PATCH', 'DELETE'}
API = re.compile(r'^/api/v1/([^/]+)/')


class AuditContextMiddleware:
    """
    Keeps the current request where the signals can read it, and logs a refused write (HTTP 403) as a Failed row.
    The user is read after the view ran, because DRF puts the authenticated user on the request while handling it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = context.set_request(request)
        try:
            response = self.get_response(request)
            if request.method in WRITE and response.status_code == 403:
                self._log_refused(request)
            return response
        finally:
            context.reset_request(token)

    @staticmethod
    def _log_refused(request):
        user = getattr(request, 'user', None)
        match = API.match(request.path)
        company = getattr(user, 'company', None) if user is not None and user.is_authenticated else None
        if not match or company is None:
            return
        safe_record(
            company=company, actor=user, actor_email=user.email, action='denied', status='failed',
            module=match.group(1).replace('-', '_'), object_repr=f'{request.method} {request.path}'[:255],
            ip_address=context.client_ip(request),
        )
