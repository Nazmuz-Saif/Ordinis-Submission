from rest_framework import serializers

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source='employee.user.email',
        read_only=True
    )

    class Meta:
        model = Attendance
        fields = [
            'id',
            'employee',
            'employee_name',
            'date',
            'check_in',
            'check_out',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'employee',
            'employee_name',
            'date',
            'check_in',
            'check_out',
            'created_at',
        ]