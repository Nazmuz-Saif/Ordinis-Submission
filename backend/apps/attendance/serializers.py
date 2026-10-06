from rest_framework import serializers

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source='employee.user.email',
        read_only=True
    )
    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True
    )
    department_name = serializers.CharField(
        source='employee.department.name',
        read_only=True,
        allow_null=True
    )
    designation_name = serializers.CharField(
        source='employee.designation.title',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Attendance
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'department_name',
            'designation_name',
            'date',
            'check_in',
            'check_out',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'department_name',
            'designation_name',
            'date',
            'check_in',
            'check_out',
            'created_at',
        ]