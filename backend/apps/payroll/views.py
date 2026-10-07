from rest_framework import viewsets

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from .models import SalaryStructure
from .serializers import SalaryStructureSerializer

FINANCE = 'manage_finance'


class SalaryStructureViewSet(PermissionRequiredMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """
    /api/v1/payroll/salary-structures/
    Every action (reading too) needs manage_finance. There is NO hierarchy rule here on
    purpose: a manager above the Accountant gets nothing unless he holds the Permission.
    """
    serializer_class = SalaryStructureSerializer

    permission_required = {
        'list': FINANCE,
        'retrieve': FINANCE,
        'create': FINANCE,
        'update': FINANCE,
        'partial_update': FINANCE,
        'destroy': FINANCE,
    }

    def get_queryset(self):
        return SalaryStructure.objects.filter(
            company=self.request.user.company
        ).select_related('employee__user')

    def perform_create(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        self._log('CREATE', instance)
