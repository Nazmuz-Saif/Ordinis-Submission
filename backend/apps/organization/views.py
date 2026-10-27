from django.db import transaction
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.exceptions import OrdinisException
from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from rbac.models import EmployeeRole

from .models import Department, Designation, Employee
from .overview import department_overview, designation_overview, in_use_message
from .services import build_access, can_see_access, get_all_subordinates
from .serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeDetailSerializer,
    EmployeeSerializer,
)


class DepartmentInUse(OrdinisException):
    code = "DEPARTMENT_IN_USE"
    message = "This Department still has employees."
    status_code = 409


class DesignationInUse(OrdinisException):
    code = "DESIGNATION_IN_USE"
    message = "This Designation is still held by employees."
    status_code = 409


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
        return (
            Department.objects.filter(company=company)
            .select_related('head__user')
            .annotate(member_total=Count('employees', distinct=True))
            .order_by('name', 'id')
        )

    def perform_create(self, serializer):
        company = self.request.user.company
        instance = serializer.save(company=company)
        self._log("CREATE", instance)

    def perform_destroy(self, instance):
        people = list(instance.employees.select_related('user').order_by('user__full_name', 'employee_code'))
        if people:
            raise DepartmentInUse(in_use_message(instance.name, people))
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"])
    def overview(self, request, pk=None):
        """GET /departments/{id}/overview/ — members, task counts and the running tasks this viewer may see."""
        department = self.get_object()  # company-scoped: another company's id returns 404
        return Response(department_overview(department, request.user.employee))


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
        return (
            Designation.objects.filter(company=company)
            .annotate(holder_total=Count('employees', distinct=True))
            .order_by('title', 'id')
        )

    def perform_create(self, serializer):
        company = self.request.user.company
        instance = serializer.save(company=company)
        self._log("CREATE", instance)

    def perform_destroy(self, instance):
        people = list(instance.employees.select_related('user').order_by('user__full_name', 'employee_code'))
        if people:
            raise DesignationInUse(in_use_message(instance.title, people))
        super().perform_destroy(instance)

    @action(detail=True, methods=["get"])
    def overview(self, request, pk=None):
        """GET /designations/{id}/overview/ — who holds this Designation, with their Department."""
        designation = self.get_object()  # company-scoped: another company's id returns 404
        return Response(designation_overview(designation))


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

    def get_serializer_class(self):
        return EmployeeDetailSerializer if self.action == "retrieve" else EmployeeSerializer

    def get_queryset(self):
        company = self.request.user.company
        return Employee.objects.filter(company=company).order_by('employee_code', 'id')

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
    def access(self, request, pk=None):
        """GET /employees/{id}/access/ — the Roles this person holds and the Permissions they really have."""
        employee = self.get_object()  # company-scoped: another company's id returns 404
        if not can_see_access(request.user.employee, employee):
            raise PermissionDenied("You may not see this person's Roles and Permissions.")
        return Response(build_access(employee))

    @action(detail=True, methods=["get"])
    def subordinates(self, request, pk=None):
        """GET /employees/{id}/subordinates/ — everyone under this employee, at any depth."""
        employee = self.get_object()  # company-scoped: another company's id returns 404
        team = get_all_subordinates(employee)
        page = self.paginate_queryset(team)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(team, many=True).data)
