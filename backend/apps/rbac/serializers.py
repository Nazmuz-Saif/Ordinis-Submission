from rest_framework import serializers

from .models import Permission, Role, EmployeeRole


class PermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Permission
        fields = ["id", "company", "name", "codename"]
        read_only_fields = ["company"]


class RoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Role
        fields = ["id", "company", "name", "permissions"]
        read_only_fields = ["company"]

    def validate_permissions(self, permissions):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        user_company = request.user.company

        for permission in permissions:
            if permission.company_id != user_company.id:
                raise serializers.ValidationError(
                    "You cannot assign a permission from another company."
                )

        return permissions


class EmployeeRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = EmployeeRole
        fields = ["id", "employee", "role"]

    def validate(self, attrs):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        employee = attrs.get("employee")
        role = attrs.get("role")
        user_company = request.user.company

        if employee.company_id != user_company.id:
            raise serializers.ValidationError(
                "You cannot assign a role to an employee from another company."
            )

        if role.company_id != user_company.id:
            raise serializers.ValidationError(
                "You cannot assign a role from another company."
            )

        return attrs