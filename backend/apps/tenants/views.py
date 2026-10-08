from rest_framework import mixins, viewsets
from core.permissions import IsCompanyActive
from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from .models import Company, CompanySettings
from .serializers import CompanySerializer, CompanySettingsSerializer


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsCompanyActive]

    def get_queryset(self):
        return Company.objects.filter(id=self.request.user.company_id)


class CompanySettingsViewSet(
    PermissionRequiredMixin,
    AuditLoggingMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    /api/v1/tenants/settings/
    Everyone in the company can read its settings. Only the manage_company_settings
    Permission can change them. There is no create or delete: every company gets exactly
    one settings row when it registers.
    """
    serializer_class = CompanySettingsSerializer
    permission_required = {
        'update': 'manage_company_settings',
        'partial_update': 'manage_company_settings',
    }

    def get_queryset(self):
        return CompanySettings.objects.filter(company=self.request.user.company).order_by('id')
