from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from rbac.models import Role
import datetime

from django.utils import timezone

from organization.models import Employee
from .models import ApprovalAction, ApprovalChain, ApprovalInstance, ApprovalStep, DelegationRule
from .services import can_act, next_step_order


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


class ApprovalActionSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source='actor.user.email', read_only=True)

    class Meta:
        model = ApprovalAction
        fields = ['id', 'step_order', 'actor', 'actor_email', 'decision', 'comment', 'created_at']
        read_only_fields = fields


class ApprovalInstanceSerializer(serializers.ModelSerializer):
    chain_name = serializers.CharField(source='approval_chain.name', read_only=True)
    target_type = serializers.CharField(source='content_type.model', read_only=True)
    target_repr = serializers.SerializerMethodField()
    requested_by_email = serializers.CharField(source='requested_by.user.email', read_only=True)
    current_step_role_name = serializers.SerializerMethodField()
    total_steps = serializers.SerializerMethodField()
    can_act = serializers.SerializerMethodField()
    actions = ApprovalActionSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalInstance
        fields = [
            'id', 'approval_chain', 'chain_name', 'target_type', 'target_repr',
            'requested_by', 'requested_by_email', 'current_step', 'current_step_role_name',
            'total_steps', 'status', 'can_act', 'actions', 'created_at',
        ]
        read_only_fields = fields

    def _step(self, obj):
        steps = list(obj.approval_chain.steps.all())  # prefetched by the view
        return next((st for st in steps if st.step_order == obj.current_step), None)

    def get_target_repr(self, obj):
        return str(obj.target) if obj.target is not None else '(deleted)'

    def get_current_step_role_name(self, obj):
        if obj.status != ApprovalInstance.STATUS_PENDING:
            return None
        step = self._step(obj)
        return step.approver_role.name if step else None

    def get_total_steps(self, obj):
        return len(obj.approval_chain.steps.all())

    def get_can_act(self, obj):
        employee = self.context['request'].user.employee
        return can_act(employee, obj, step=self._step(obj), role_ids=self.context.get('role_ids'))


class DelegationRuleSerializer(serializers.ModelSerializer):
    delegator_email = serializers.CharField(source='delegator.user.email', read_only=True)
    delegate_email = serializers.CharField(source='delegate.user.email', read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = DelegationRule
        fields = [
            'id', 'delegator', 'delegator_email', 'delegate', 'delegate_email',
            'start_date', 'end_date', 'reason', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'delegator', 'created_at']

    def get_fields(self):
        fields = super().get_fields()
        # Only colleagues of the same company can be chosen.
        scope_queryset(fields['delegate'], Employee, company_of(self))
        return fields

    def get_is_active(self, obj):
        return obj.start_date <= timezone.localdate() <= obj.end_date

    def validate(self, attrs):
        request = self.context['request']
        if attrs['delegate'] == request.user.employee:
            raise serializers.ValidationError({'delegate': 'You cannot delegate to yourself.'})
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'The end date cannot be before the start date.'})
        if attrs['end_date'] < timezone.localdate():
            raise serializers.ValidationError({'end_date': 'The end date cannot be in the past.'})
        return attrs
