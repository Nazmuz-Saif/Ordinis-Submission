from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Every field is read-only: the log is written by the system, never by a client."""
    action_label = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'created_at', 'actor_email', 'action', 'action_label', 'status', 'module', 'model_name',
            'object_id', 'object_repr', 'changed_fields', 'ip_address',
        ]
        read_only_fields = fields
