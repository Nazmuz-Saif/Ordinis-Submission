from rest_framework import viewsets
from core.permissions import IsCompanyActive
from core.mixins import AuditLoggingMixin
from .models import Company, CompanySettings
from .serializers import CompanySerializer, CompanySettingsSerializer


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [IsCompanyActive]

    def get_queryset(self):
        return Company.objects.filter(id=self.request.user.company_id)


class CompanySettingsViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = CompanySettingsSerializer
    permission_classes = [IsCompanyActive]

    def get_queryset(self):
        return CompanySettings.objects.filter(company=self.request.user.company)