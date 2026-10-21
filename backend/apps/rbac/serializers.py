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
        fields = ['id', 'codename', 'name', 'module', 'description']
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

    # How many employees hold this Role (the view annotates it so a list costs one query).
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'is_system_default',
            'permissions', 'permission_details', 'employee_count',
        ]
        read_only_fields = ['id', 'is_system_default', 'employee_count']

    def get_employee_count(self, obj):
        count = getattr(obj, 'holder_count', None)
        return count if count is not None else obj.employee_roles.count()

    def validate_name(self, value):
        """One Role name per company (the database enforces it; this gives a clear 400 instead of a 500)."""
        value = value.strip()
        company = self.context['request'].user.company
        clash = Role.objects.filter(company=company, name__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError('A Role with this name already exists.')
        return value


class RoleDetailSerializer(RoleSerializer):
    """The Role detail page: the same fields plus the employees who hold the Role."""
    employees = serializers.SerializerMethodField()

    class Meta(RoleSerializer.Meta):
        fields = RoleSerializer.Meta.fields + ['employees']
        read_only_fields = RoleSerializer.Meta.read_only_fields + ['employees']

    def get_employees(self, obj):
        links = obj.employee_roles.select_related('employee__user').order_by('employee__employee_code')
        return [
            {'id': str(link.employee_id), 'employee_code': link.employee.employee_code, 'email': link.employee.user.email}
            for link in links
        ]


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
