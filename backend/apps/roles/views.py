from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsCompanyActive
from core.mixins import AuditLoggingMixin
from .models import Department, Designation, Employee, EmployeeRole
from .serializers import (
    DepartmentSerializer,
    DesignationSerializer,
    EmployeeSerializer,
    EmployeeRoleSerializer,
)


class DepartmentViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_required = {
        'create': 'manage_departments',
        'update': 'manage_departments',
        'partial_update': 'manage_departments',
        'destroy': 'manage_departments',
    }

    def get_queryset(self):
        return Department.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class DesignationViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = DesignationSerializer
    permission_required = {
        'create': 'manage_departments',
        'update': 'manage_departments',
        'partial_update': 'manage_departments',
        'destroy': 'manage_departments',
    }

    def get_queryset(self):
        return Designation.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class EmployeeViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_required = {
        'create': 'manage_employees',
        'update': 'manage_employees',
        'partial_update': 'manage_employees',
        'destroy': 'manage_employees',
    }

    def get_queryset(self):
        return Employee.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class EmployeeRoleViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    CRUD /api/v1/organization/employee-roles/
    Assign or revoke roles to employees within the company.
    """
    serializer_class = EmployeeRoleSerializer
    permission_classes = [IsAuthenticated, IsCompanyActive]

    def get_queryset(self):
        return EmployeeRole.objects.filter(
            company=self.request.user.company
        ).select_related('employee__user', 'role')

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)