from rest_framework import serializers

from .models import Invoice, PaymentSubmission, SubscriptionPlan


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
                  'status_label', 'issued_on', 'due_on', 'paid_on', 'payment_method', 'transaction_id']
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    """A payment as the company sees it. The reviewer's identity is not shown, only the decision and the note."""
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    method_label = serializers.CharField(source='get_method_display', read_only=True)
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.user.full_name', read_only=True, default='')
    submitted_by_email = serializers.CharField(source='submitted_by.user.email', read_only=True, default='')
    invoice_number = serializers.CharField(source='invoice.number', read_only=True, default=None)

    class Meta:
        model = PaymentSubmission
        fields = [
            'id', 'plan', 'plan_name', 'months', 'amount', 'currency', 'method', 'method_label', 'payer_name',
            'payer_number', 'transaction_id', 'kind', 'kind_label', 'status', 'status_label', 'submitted_by_name',
            'submitted_by_email', 'reviewed_at', 'review_note', 'period_start', 'period_end', 'invoice',
            'invoice_number', 'created_at',
        ]
        read_only_fields = fields


class AdminPaymentSerializer(PaymentSerializer):
    """The same, for the platform team: also which company and who decided."""
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_subdomain = serializers.CharField(source='company.subdomain', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta(PaymentSerializer.Meta):
        fields = PaymentSerializer.Meta.fields + ['company', 'company_name', 'company_subdomain', 'reviewed_by_name']
        read_only_fields = fields

    def get_reviewed_by_name(self, obj):
        user = obj.reviewed_by
        return (user.full_name or user.email) if user else None


class PaymentSubmitSerializer(serializers.Serializer):
    """What a company sends. The amount is NOT an input: it is the server's quote. `amount` is only the price the
    person saw, so a price that changed in between is refused instead of being charged silently."""
    plan = serializers.CharField()
    months = serializers.CharField()
    method = serializers.CharField()
    payer_name = serializers.CharField(allow_blank=True)
    payer_number = serializers.CharField(allow_blank=True)
    transaction_id = serializers.CharField(allow_blank=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
