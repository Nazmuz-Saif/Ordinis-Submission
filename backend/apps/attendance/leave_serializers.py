from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from .leave_models import LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'days_allowed_per_year', 'created_at']
        read_only_fields = ['id', 'created_at']  # company is set by the server, never taken from the client

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Give the leave type a name.')
        company = company_of(self)
        clash = LeaveType.objects.filter(company=company, name__iexact=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if company and clash.exists():
            raise serializers.ValidationError(f'{value} already exists.')
        return value


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Shown for the list. Creating goes through apply_leave, which does every check."""
    leave_type_name = serializers.CharField(source='leave_type.name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ['id', 'leave_type', 'leave_type_name', 'start_date', 'end_date', 'days', 'reason', 'status', 'created_at']
        read_only_fields = ['id', 'days', 'status', 'created_at']

    def get_fields(self):
        fields = super().get_fields()
        scope_queryset(fields['leave_type'], LeaveType, company_of(self))
        return fields
