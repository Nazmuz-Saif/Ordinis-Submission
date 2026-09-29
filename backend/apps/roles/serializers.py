from rest_framework import serializers
from .models import Permission, Role


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
