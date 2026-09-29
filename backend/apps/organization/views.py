from rest_framework import viewsets

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin, get_effective_company

from .models import Department, Designation, Employee, EmployeeRole
from .serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeSerializer,
    EmployeeRoleSerializer,
)


class DepartmentViewSet(
    PermissionRequiredMixin,
    AuditLoggingMixin,
    viewsets.ModelViewSet,
):
    serializer_class = DepartmentSerializer

    permission_required = {
        "create": "manage_departments",
        "update": "manage_departments",
        "partial_update": "manage_departments",
        "destroy": "manage_departments",
    }

    def get_queryset(self):
        company = get_effective_company(self.request.user)
        return Department.objects.filter(company=company)

    def perform_create(self, serializer):
        company = get_effective_company(self.request.user)
        instance = serializer.save(company=company)
        self._log("CREATE", instance)


class DesignationViewSet(
    PermissionRequiredMixin,
    AuditLoggingMixin,
    viewsets.ModelViewSet,
):
    serializer_class = DesignationSerializer

    permission_required = {
        "create": "manage_designations",
        "update": "manage_designations",
        "partial_update": "manage_designations",
        "destroy": "manage_designations",
    }

    def get_queryset(self):
        company = get_effective_company(self.request.user)
        return Designation.objects.filter(company=company)

    def perform_create(self, serializer):
        company = get_effective_company(self.request.user)
        instance = serializer.save(company=company)
        self._log("CREATE", instance)


class EmployeeViewSet(
    PermissionRequiredMixin,
    AuditLoggingMixin,
    viewsets.ModelViewSet,
):
    serializer_class = EmployeeSerializer

    permission_required = {
        "create": "manage_employees",
        "update": "manage_employees",
        "partial_update": "manage_employees",
        "destroy": "manage_employees",
    }

    def get_queryset(self):
        company = get_effective_company(self.request.user)
        return Employee.objects.filter(company=company)

    def perform_create(self, serializer):
        company = get_effective_company(self.request.user)
        instance = serializer.save(company=company)
        self._log("CREATE", instance)


class EmployeeRoleViewSet(
    PermissionRequiredMixin,
    AuditLoggingMixin,
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
        company = get_effective_company(self.request.user)
        return EmployeeRole.objects.filter(company=company).select_related(
            "employee__user",
            "role",
        )

    def perform_create(self, serializer):
        company = get_effective_company(self.request.user)
        instance = serializer.save(company=company)
        self._log("CREATE", instance)