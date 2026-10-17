from rest_framework import serializers

from .models import Invoice, SubscriptionPlan


class PlanSerializer(serializers.ModelSerializer):
    unlimited = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'max_employees', 'unlimited', 'price_monthly', 'currency']
        read_only_fields = fields

    def get_unlimited(self, obj):
        return obj.max_employees is None


class InvoiceSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'number', 'plan_name', 'period_start', 'period_end', 'amount', 'currency', 'status',
                  'status_label', 'issued_on', 'due_on', 'paid_on']
        read_only_fields = fields
