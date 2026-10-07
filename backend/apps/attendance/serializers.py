from rest_framework import serializers

from .models import Attendance
from .services import company_zone


class AttendanceSerializer(serializers.ModelSerializer):
    check_in_time = serializers.SerializerMethodField()
    check_out_time = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'date', 'check_in', 'check_out', 'check_in_time', 'check_out_time', 'status']
        read_only_fields = fields

    def _local(self, value, obj):
        if value is None:
            return None
        return value.astimezone(company_zone(obj.company)).strftime('%H:%M')

    def get_check_in_time(self, obj):
        return self._local(obj.check_in, obj)

    def get_check_out_time(self, obj):
        return self._local(obj.check_out, obj)

    def get_status(self, obj):
        return 'checked_out' if obj.check_out else 'checked_in'
