from rest_framework import viewsets, mixins
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from core.permissions import IsCompanyActive
from core.mixins import AuditLoggingMixin, PermissionRequiredMixin

from .models import EmployeeRole, Permission, Role
from .serializers import EmployeeRoleSerializer, PermissionSerializer, RoleSerializer


class PermissionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    GET /api/v1/rbac/permissions/
    Read-only — returns all system-wide permissions.
    Any authenticated user can see the list.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsCompanyActive]


class RoleViewSet(PermissionRequiredMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """
    CRUD /api/v1/rbac/roles/
    Company-scoped — each company only sees its own roles.
    """
    serializer_class = RoleSerializer

    permission_required = {
        "create": "manage_roles",
        "update": "manage_roles",
        "partial_update": "manage_roles",
        "destroy": "manage_roles",
    }

    def get_queryset(self):
        return Role.objects.filter(company=self.request.user.company).prefetch_related("permissions")

    def perform_create(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        self._log("CREATE", instance)

    def perform_update(self, serializer):
        if serializer.instance.is_system_default:
            raise ValidationError("The system CEO role cannot be edited.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.is_system_default:
            raise ValidationError("The system CEO role cannot be deleted.")
        if instance.approval_steps.exists():
            raise ValidationError("This role is used by an approval chain step. Change that step first.")
        super().perform_destroy(instance)


class EmployeeRoleViewSet(
    PermissionRequiredMixin,
    AuditLoggingMixin,
    viewsets.ModelViewSet,
):
    serializer_class = EmployeeRoleSerializer

    permission_required = {
        "create": "assign_roles",
        "update": "assign_roles",
        "partial_update": "assign_roles",
        "destroy": "assign_roles",
    }

    def get_queryset(self):
        company = self.request.user.company
        return EmployeeRole.objects.filter(company=company).select_related(
            "employee__user",
            "role",
        )

    def perform_create(self, serializer):
        company = self.request.user.company
        instance = serializer.save(company=company)
        self._log("CREATE", instance)

    def perform_destroy(self, instance):
        # Never let the company lose its last full-access (CEO) holder.
        if instance.role.is_system_default:
            holders = EmployeeRole.objects.filter(company=instance.company, role=instance.role).count()
            if holders <= 1:
                raise ValidationError("You cannot remove the last holder of the system CEO role.")
        super().perform_destroy(instance)
