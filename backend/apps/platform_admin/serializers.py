from rest_framework import serializers

from tenants.models import Company
from .models import ImpersonationLog, PlatformActionLog, SupportAccessRequest, SupportTicket
from .services import effective_status


class AccessRequestSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)
    requested_by_email = serializers.CharField(source='requested_by.email', read_only=True)
    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportAccessRequest
        fields = [
            'id', 'company', 'company_name', 'requested_by_email', 'reason', 'status',
            'decided_by_name', 'decided_at', 'expires_at', 'created_at',
        ]
        read_only_fields = fields

    def get_status(self, obj):
        return effective_status(obj)

    def get_decided_by_name(self, obj):
        employee = obj.decided_by
        return employee.user.email if employee else None


class AccessRequestCreateSerializer(serializers.Serializer):
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())
    reason = serializers.CharField(allow_blank=True)


class ImpersonationLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.email', read_only=True)

    class Meta:
        model = ImpersonationLog
        fields = ['id', 'access_request', 'actor_email', 'method', 'endpoint', 'detail', 'created_at']
        read_only_fields = fields


class CompanyAdminSerializer(serializers.ModelSerializer):
    """What the admin panel may know about a company: who it is, whether it is active, and counts of
    OUR OWN objects. Never anything about its employees, tasks or salaries."""
    open_tickets = serializers.IntegerField(read_only=True)
    pending_requests = serializers.IntegerField(read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'subdomain', 'industry', 'is_active', 'created_at', 'open_tickets', 'pending_requests']
        read_only_fields = fields


class TicketSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = ['id', 'company', 'company_name', 'created_by_email', 'subject', 'description', 'status', 'created_at', 'resolved_at']
        read_only_fields = ['id', 'company', 'company_name', 'created_by_email', 'status', 'created_at', 'resolved_at']

    def get_created_by_email(self, obj):
        return obj.created_by.user.email if obj.created_by else None


class PlatformActionLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.email', read_only=True)

    class Meta:
        model = PlatformActionLog
        fields = ['id', 'actor_email', 'company', 'company_name', 'action', 'note', 'created_at']
        read_only_fields = fields
