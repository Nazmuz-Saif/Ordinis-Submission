from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsCompanyActive, HasPermission


def get_effective_company(user):
    from tenants.models import Company
    if user and user.is_authenticated and getattr(user, 'company', None):
        return user.company
    company = Company.objects.first()
    if not company:
        company = Company.objects.create(name="Ordinis", subdomain="ordinis")
    if user and user.is_authenticated and not getattr(user, 'company', None):
        user.company = company
        user.save(update_fields=['company'])
    return company


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
    Mixin for DRF ViewSets: automatically logs create/update/destroy
    actions to AuditLog, tagged with the acting employee, the model
    name, and the affected object's id.
    """

    def perform_create(self, serializer):
        instance = serializer.save()
        self._log("CREATE", instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._log("UPDATE", instance)

    def perform_destroy(self, instance):
        self._log("DELETE", instance)
        instance.delete()

    def _log(self, action, instance):
        employee = getattr(self.request.user, 'employee', None)
        if not employee:
            return

        try:
            from audit_log.models import AuditLog
        except ModuleNotFoundError:
            # audit_log app not present in this build scope yet — skip logging
            return

        AuditLog.objects.create(
            actor=employee,
            action=action,
            model_name=instance.__class__.__name__,
            object_id=getattr(instance, 'id', None),
            ip_address=self._get_client_ip(),
        )
        return

    def _get_client_ip(self):
        forwarded = self.request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded:
            return forwarded.split(",")[0].strip()

        return self.request.META.get("REMOTE_ADDR")


class PermissionRequiredMixin:
    """
    Applies authentication, company-active checking, and
    action-based permission checking to a DRF ViewSet.
    """

    permission_classes = [
        IsAuthenticated,
        IsCompanyActive,
        HasPermission,
    ]

    permission_required = None

    def get_required_permission(self):
        required = self.permission_required

        if isinstance(required, dict):
            return required.get(getattr(self, "action", None))

        return required