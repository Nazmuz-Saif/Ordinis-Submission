from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from rbac.models import EmployeeRole

from .models import Department, Designation, Employee
from .services import get_all_subordinates
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
        company = self.request.user.company
        return Department.objects.filter(company=company)

    def perform_create(self, serializer):
        company = self.request.user.company
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
        company = self.request.user.company
        return Designation.objects.filter(company=company)

    def perform_create(self, serializer):
        company = self.request.user.company
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
        company = self.request.user.company
        return Employee.objects.filter(company=company)

    def perform_create(self, serializer):
        company = self.request.user.company
        instance = serializer.save(company=company)
        self._log("CREATE", instance)

    def perform_destroy(self, instance):
        me = getattr(self.request.user, "employee", None)
        if me is not None and instance.id == me.id:
            raise ValidationError("You cannot delete your own employee record.")
        if instance.direct_reports.exists():
            raise ValidationError(
                "This employee still has team members. Reassign them to another manager first."
            )
        for assignment in EmployeeRole.objects.filter(employee=instance, role__is_system_default=True):
            holders = EmployeeRole.objects.filter(role=assignment.role).count()
            if holders <= 1:
                raise ValidationError("You cannot delete the last holder of the system CEO role.")

        user = instance.user
        with transaction.atomic():
            super().perform_destroy(instance)
            # Removing the employee must also end their access: an active login with no
            # employee record could otherwise still sign in and read company data.
            user.is_active = False
            user.save(update_fields=["is_active"])

    @action(detail=True, methods=["get"])
    def subordinates(self, request, pk=None):
        """GET /employees/{id}/subordinates/ — everyone under this employee, at any depth."""
        employee = self.get_object()  # company-scoped: another company's id returns 404
        team = get_all_subordinates(employee)
        return Response(self.get_serializer(team, many=True).data)
