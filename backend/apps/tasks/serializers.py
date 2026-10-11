from django.core.validators import URLValidator
from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from organization.models import Employee
from .models import Task, TaskProgressLog
from .services import TaskError, check_transition


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_email = serializers.CharField(source='assigned_to.user.email', read_only=True)
    assigned_by_email = serializers.CharField(source='assigned_by.user.email', read_only=True, default=None)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'assigned_to', 'assigned_to_email',
            'assigned_by', 'assigned_by_email', 'priority', 'deadline', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'assigned_by', 'created_at']

    def get_fields(self):
        fields = super().get_fields()
        # The assignee must belong to the same company as the person creating the task.
        scope_queryset(fields['assigned_to'], Employee, company_of(self))
        return fields

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Title cannot be empty.')
        return value

    def validate_status(self, value):
        if self.instance is None:
            if value != Task.STATUS_NOT_STARTED:
                raise serializers.ValidationError('A new task always starts as Not Started.')
            return value
        if value != self.instance.status:
            try:
                check_transition(self.instance.status, value)
            except TaskError as exc:
                raise serializers.ValidationError(str(exc))
        return value


class TaskProgressSerializer(serializers.ModelSerializer):
    """One progress note. There is deliberately no file field: nothing is ever uploaded."""
    employee_email = serializers.CharField(source='employee.user.email', read_only=True)
    external_reference_url = serializers.CharField(
        required=False, allow_blank=True, max_length=500,
        validators=[URLValidator(schemes=['http', 'https'])],
    )

    class Meta:
        model = TaskProgressLog
        fields = [
            'id', 'date', 'employee_email', 'update_text', 'progress_percent',
            'blocker_text', 'external_reference_url', 'created_at',
        ]
        read_only_fields = ['id', 'date', 'employee_email', 'created_at']

    def validate_update_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Write what you did today.')
        return value

    def validate_progress_percent(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Progress must be between 0 and 100.')
        return value
