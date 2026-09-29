from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsCompanyActive
from core.mixins import AuditLoggingMixin
from .models import Permission, Role
from .serializers import PermissionSerializer, RoleSerializer


class PermissionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    GET /api/v1/roles/permissions/
    Read-only — returns all system-wide permissions.
    Any authenticated user can see the list.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsCompanyActive]


class RoleViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    CRUD /api/v1/roles/roles/
    Company-scoped — each company only sees its own roles.
    """
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsCompanyActive]

    def get_queryset(self):
        return Role.objects.filter(
            company=self.request.user.company
        ).prefetch_related('permissions')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

