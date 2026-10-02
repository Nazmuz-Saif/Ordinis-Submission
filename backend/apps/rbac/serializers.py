from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from organization.models import Employee
from .models import EmployeeRole, Permission, Role


class PermissionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer — permissions are system-defined,
    users cannot create/edit/delete them.
    """
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'module']
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    """
    Full CRUD serializer for Roles.
    - 'permissions' field: accepts a list of Permission UUIDs (for create/update)
    - 'permission_details' field: returns full Permission objects (for reading)
    """
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, required=False
    )
    permission_details = PermissionSerializer(
        source='permissions', many=True, read_only=True
    )

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'is_system_default',
            'permissions', 'permission_details',
        ]
        read_only_fields = ['id', 'is_system_default']


class EmployeeRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.CharField(source='employee.user.email', read_only=True)

    class Meta:
        model = EmployeeRole
        fields = ['id', 'employee', 'role', 'role_name', 'employee_code', 'employee_email', 'company']
        read_only_fields = ['id', 'company']

    def get_fields(self):
        fields = super().get_fields()
        company = company_of(self)
        # Cannot assign another company's Role (or Employee) — prevents cross-tenant privilege escalation.
        scope_queryset(fields['employee'], Employee, company)
        scope_queryset(fields['role'], Role, company)
        return fields
