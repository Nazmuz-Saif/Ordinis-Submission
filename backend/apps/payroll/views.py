from rest_framework import viewsets

from core.permissions import HasPermission
from .models import SalaryStructure
from .serializers import SalaryStructureSerializer


class SalaryStructureViewSet(viewsets.ModelViewSet):
    serializer_class = SalaryStructureSerializer
    permission_classes = [HasPermission]
    required_permission = 'finance'

    def get_queryset(self):
        company = self.request.user.company

        return SalaryStructure.objects.filter(
            company=company
        ).select_related(
            'employee__user',
            'employee__department',
            'employee__designation',
        )

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company
        )