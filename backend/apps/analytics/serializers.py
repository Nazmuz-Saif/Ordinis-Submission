from rest_framework import serializers

from .models import CompanyHealthSnapshot


class SnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyHealthSnapshot
        fields = ['id', 'date', 'headcount', 'attendance_rate', 'task_completion_rate', 'open_tasks',
                  'overdue_tasks', 'health_score']
        read_only_fields = fields
