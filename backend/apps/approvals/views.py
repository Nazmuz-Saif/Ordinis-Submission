from django.db.models import F, Q
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from .models import ApprovalAction, ApprovalChain, ApprovalInstance, ApprovalStep, DelegationRule
from .serializers import (
    ApprovalChainSerializer, ApprovalInstanceSerializer, ApprovalStepSerializer,
    DelegationRuleSerializer,
)
from .services import (
    ApprovalError, NotAnApprover, chain_has_pending, compact_steps,
    can_act, decide, effective_role_ids, reorder_steps,
)

MANAGE = 'manage_approval_chains'


class ApprovalChainViewSet(PermissionRequiredMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """
    /api/v1/approvals/chains/        Any employee can read; writing needs manage_approval_chains.
    POST /chains/{id}/reorder/       body: {"step_ids": [...]} - the new step order.
    """
    serializer_class = ApprovalChainSerializer

    permission_required = {
        'create': MANAGE,
        'update': MANAGE,
        'partial_update': MANAGE,
        'destroy': MANAGE,
        'reorder': MANAGE,
    }

    def get_queryset(self):
        return (
            ApprovalChain.objects.filter(company=self.request.user.company)
            .prefetch_related('steps__approver_role')
        )

    def perform_create(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        self._log('CREATE', instance)

    def perform_destroy(self, instance):
        if instance.instances.exists():
            raise ValidationError('This chain already has requests in its history and cannot be deleted.')
        super().perform_destroy(instance)

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        chain = self.get_object()
        if chain_has_pending(chain):
            raise ValidationError('This chain has pending requests. Its steps cannot be changed right now.')
        step_ids = request.data.get('step_ids')
        if not isinstance(step_ids, list):
            raise ValidationError({'step_ids': 'A list of step ids is required.'})
        try:
            reorder_steps(chain, step_ids)
        except ValueError as exc:
            raise ValidationError({'step_ids': str(exc)})
        self._log('UPDATE', chain)
        chain = self.get_queryset().get(pk=chain.pk)
        return Response(self.get_serializer(chain).data)


class ApprovalStepViewSet(PermissionRequiredMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """
    /api/v1/approvals/steps/         Optional filter: ?chain=<chain id>
    """
    serializer_class = ApprovalStepSerializer

    permission_required = {
        'create': MANAGE,
        'update': MANAGE,
        'partial_update': MANAGE,
        'destroy': MANAGE,
    }

    def get_queryset(self):
        qs = ApprovalStep.objects.filter(
            approval_chain__company=self.request.user.company
        ).select_related('approver_role', 'approval_chain')
        chain_id = self.request.query_params.get('chain')
        if chain_id:
            qs = qs.filter(approval_chain_id=chain_id)
        return qs

    def _ensure_unlocked(self, chain):
        if chain_has_pending(chain):
            raise ValidationError('This chain has pending requests. Its steps cannot be changed right now.')

    def perform_create(self, serializer):
        self._ensure_unlocked(serializer.validated_data['approval_chain'])
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._ensure_unlocked(serializer.instance.approval_chain)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        chain = instance.approval_chain
        self._ensure_unlocked(chain)
        super().perform_destroy(instance)
        compact_steps(chain)  # keep orders 1..n with no gap


class ApprovalInstanceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    /api/v1/approvals/instances/            Requests I started, can decide, or have decided
                                            (users with manage_approval_chains see the whole company).
    /api/v1/approvals/instances/?mine=pending   Only requests waiting for MY decision.
    POST /instances/{id}/approve/           body: {"comment": "..."}  (optional)
    POST /instances/{id}/reject/            body: {"comment": "..."}  (required)
    Instances are created by other modules (e.g. leave), never through this API.
    """
    serializer_class = ApprovalInstanceSerializer

    def _employee(self):
        return self.request.user.employee

    def get_queryset(self):
        employee = self._employee()
        qs = (
            ApprovalInstance.objects.filter(company=employee.company)
            .select_related('approval_chain', 'content_type', 'requested_by__user')
            .prefetch_related('approval_chain__steps__approver_role', 'actions__actor__user')
        )
        if not employee.has_permission('manage_approval_chains'):
            roles = effective_role_ids(employee)
            qs = qs.filter(
                Q(requested_by=employee)
                | Q(actions__actor=employee)
                | Q(status=ApprovalInstance.STATUS_PENDING,
                    approval_chain__steps__approver_role_id__in=roles,
                    approval_chain__steps__step_order=F('current_step'))
            ).distinct()
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request and self.request.user.is_authenticated:
            context['role_ids'] = effective_role_ids(self._employee())
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        items = list(queryset)
        if request.query_params.get('mine') == 'pending':
            employee, roles = self._employee(), effective_role_ids(self._employee())
            items = [i for i in items if can_act(employee, i, role_ids=roles)]
        page = self.paginate_queryset(items)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(items, many=True).data)

    def _decide(self, request, pk, decision):
        instance = self.get_object()
        try:
            decide(instance.pk, self._employee(), decision, request.data.get('comment', ''))
        except NotAnApprover as exc:
            raise PermissionDenied(str(exc))
        except ApprovalError as exc:
            raise ValidationError(str(exc))
        fresh = self.get_queryset().get(pk=instance.pk)
        return Response(self.get_serializer(fresh).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, pk, ApprovalAction.DECISION_APPROVED)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, pk, ApprovalAction.DECISION_REJECTED)


class DelegationRuleViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin, AuditLoggingMixin, viewsets.GenericViewSet,
):
    """
    /api/v1/approvals/delegations/
    Everyone manages only their OWN delegations: "while I am away, <delegate> may decide
    what waits for my roles". The delegator is always the logged-in employee.
    The list also shows delegations that were handed TO you, read-only.
    """
    serializer_class = DelegationRuleSerializer

    def get_queryset(self):
        employee = self.request.user.employee
        return (
            DelegationRule.objects.filter(company=employee.company)
            .filter(Q(delegator=employee) | Q(delegate=employee))
            .select_related('delegator__user', 'delegate__user')
        )

    def perform_create(self, serializer):
        employee = self.request.user.employee
        instance = serializer.save(company=employee.company, delegator=employee)
        self._log('CREATE', instance)

    def perform_destroy(self, instance):
        if instance.delegator_id != self.request.user.employee.id:
            raise PermissionDenied('Only the person who created a delegation can remove it.')
        super().perform_destroy(instance)
