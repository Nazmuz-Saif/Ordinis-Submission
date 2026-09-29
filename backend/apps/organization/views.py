from rest_framework import viewsets

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin

from .models import Department, Designation, Employee
from .serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeSerializer,
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
        return Department.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        instance = serializer.save(
            company=self.request.user.company
        )
        self._log("CREATE", instance)


class DesignationViewSet(
    PermissionRequiredMixin,
    AuditLoggingMixin,
    viewsets.ModelViewSet,
):
    serializer_class = DesignationSerializer

    permission_required = {
        "create": "manage_departments",
        "update": "manage_departments",
        "partial_update": "manage_departments",
        "destroy": "manage_departments",
    }

    def get_queryset(self):
        return Designation.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        instance = serializer.save(
            company=self.request.user.company
        )
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
        return Employee.objects.filter(
            company=self.request.user.company
        )

    def perform_create(self, serializer):
        instance = serializer.save(
            company=self.request.user.company
        )
        self._log("CREATE", instance)