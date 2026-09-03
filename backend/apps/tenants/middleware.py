from django.utils.deprecation import MiddlewareMixin


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Attaches request.company for any authenticated, session-based
    request (Django Admin, browsable API session auth) and blocks
    access outright if that company has been suspended.

    Note: DRF's JWT authentication happens AFTER middleware runs, so
    request.user here reflects session auth only. The equivalent
    check for JWT-authenticated API requests is core.permissions.IsCompanyActive,
    which must be included in every API view's permission_classes.
    """

    def process_request(self, request):
        request.company = None

        user = getattr(request, 'user', None)
        if user and user.is_authenticated and getattr(user, 'company_id', None):
            request.company = user.company

            if not request.company.is_active:
                from django.http import JsonResponse
                return JsonResponse(
                    {
                        "success": False,
                        "error": {
                            "code": "COMPANY_SUSPENDED",
                            "message": "This company's account is currently suspended.",
                        },
                    },
                    status=403,
                )
        return None