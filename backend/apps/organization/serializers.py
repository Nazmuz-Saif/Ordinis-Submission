from django.db import transaction
from rest_framework import serializers
from accounts.models import User
from .models import Department, Designation, Employee
from .models import EmployeeRole


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'company']
        read_only_fields = ['id', 'company']


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['id', 'title', 'company']
        read_only_fields = ['id', 'company']


class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_title = serializers.CharField(source='designation.title', read_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Employee
        fields = [
            'id', 'email', 'password', 'company', 'department', 'department_name',
            'designation', 'designation_title', 'reports_to', 'employee_code',
        ]
        read_only_fields = ['id', 'company']

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        company = validated_data.pop('company')
        with transaction.atomic():
            user = User.objects.create_user(email=email, password=password, company=company)
            employee = Employee.objects.create(user=user, company=company, **validated_data)
        return employee

class EmployeeRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    employee_email = serializers.CharField(source='employee.user.email', read_only=True)

    class Meta:
        model = EmployeeRole
        fields = ['id', 'employee', 'role', 'role_name', 'employee_code', 'employee_email', 'company']
        read_only_fields = ['id', 'company']

    def create(self, validated_data):
        company = self.context['request'].user.company
        return EmployeeRole.objects.create(company=company, **validated_data)

