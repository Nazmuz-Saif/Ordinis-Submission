from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from rbac.models import Role
from .models import ApprovalChain, ApprovalStep
from .services import next_step_order


class ApprovalStepSerializer(serializers.ModelSerializer):
    approver_role_name = serializers.CharField(source='approver_role.name', read_only=True)
    step_order = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = ApprovalStep
        fields = ['id', 'approval_chain', 'step_order', 'approver_role', 'approver_role_name']
        read_only_fields = ['id']
        validators = []  # uniqueness is checked in validate() so step_order can be auto-filled

    def get_fields(self):
        fields = super().get_fields()
        company = company_of(self)
        # Only the user's own company's chains and roles can be chosen.
        scope_queryset(fields['approval_chain'], ApprovalChain, company)
        scope_queryset(fields['approver_role'], Role, company)
        return fields

    def validate(self, attrs):
        if self.instance and 'approval_chain' in attrs and attrs['approval_chain'] != self.instance.approval_chain:
            raise serializers.ValidationError('A step cannot be moved to another chain.')

        chain = attrs.get('approval_chain') or (self.instance.approval_chain if self.instance else None)
        order = attrs.get('step_order')
        if order is not None:
            clash = ApprovalStep.objects.filter(approval_chain=chain, step_order=order)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({'step_order': 'This chain already has a step with that order.'})
        return attrs

    def create(self, validated_data):
        if validated_data.get('step_order') is None:
            validated_data['step_order'] = next_step_order(validated_data['approval_chain'])
        return super().create(validated_data)


class ApprovalChainSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalChain
        fields = ['id', 'name', 'applies_to_module', 'steps']
        read_only_fields = ['id']
        validators = []

    def validate_name(self, value):
        company = company_of(self)
        clash = ApprovalChain.objects.filter(company=company, name=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError('Your company already has a chain with this name.')
        return value
