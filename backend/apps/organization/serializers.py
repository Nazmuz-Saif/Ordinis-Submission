from rest_framework import serializers
from .models import Department, Designation, Employee


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

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'company', 'department', 'department_name',
            'designation', 'designation_title', 'reports_to', 'employee_code',
        ]
        read_only_fields = ['id', 'company']