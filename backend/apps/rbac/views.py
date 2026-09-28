from rest_framework import viewsets

from core.mixins import PermissionRequiredMixin

from .models import Permission, Role, EmployeeRole
from .serializers import (
    PermissionSerializer,
    RoleSerializer,
    EmployeeRoleSerializer,
)


class PermissionViewSet(
    PermissionRequiredMixin,
    viewsets.ModelViewSet,
):
    serializer_class = PermissionSerializer

    permission_required = {
        "create": "manage_roles",
        "update": "manage_roles",
        "partial_update": "manage_roles",
        "destroy": "manage_roles",
    }

    def get_queryset(self):
        return Permission.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company
        )


class RoleViewSet(
    PermissionRequiredMixin,
    viewsets.ModelViewSet,
):
    serializer_class = RoleSerializer

    permission_required = {
        "create": "manage_roles",
        "update": "manage_roles",
        "partial_update": "manage_roles",
        "destroy": "manage_roles",
    }

    def get_queryset(self):
        return Role.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        serializer.save(
            company=self.request.user.company
        )


class EmployeeRoleViewSet(
    PermissionRequiredMixin,
    viewsets.ModelViewSet,
):
    serializer_class = EmployeeRoleSerializer

    permission_required = {
        "create": "manage_roles",
        "update": "manage_roles",
        "partial_update": "manage_roles",
        "destroy": "manage_roles",
    }

    def get_queryset(self):
        return EmployeeRole.objects.filter(
            employee__company=self.request.user.company
        )
    