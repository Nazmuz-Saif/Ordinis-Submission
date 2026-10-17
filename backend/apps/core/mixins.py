from rest_framework.response import Response


class StandardResponseMixin:
    """
    Ensures every successful response follows the same envelope:
    { success, data, message }
    """

    def success_response(self, data=None, message="Success", status_code=200):
        return Response(
            {
                "success": True,
                "data": data,
                "message": message,
            },
            status=status_code,
        )


class AuditLoggingMixin:
    """
    Formerly logged create/update/destroy from the ViewSet. Now a no-op: see audit_log.signals.
    """

    # Kept so the ViewSets that mix it in (and call self._log) keep working. Logging is now done in one place for
    # every model, by audit_log.signals (it also covers custom actions, services and Break-Glass reads), so this
    # does nothing and cannot log a second row for the same action.
    def _log(self, action, instance):
        return None


# PermissionRequiredMixin lives in rbac/decorators.py (per the SDS); re-exported here
# so existing `from core.mixins import PermissionRequiredMixin` imports keep working.
from rbac.decorators import PermissionRequiredMixin  # noqa: E402,F401
