from rest_framework.permissions import IsAuthenticated

from core.permissions import IsCompanyActive, HasPermission


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
