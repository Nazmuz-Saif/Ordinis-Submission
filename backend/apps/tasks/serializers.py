from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from organization.models import Employee
from .models import Task
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
