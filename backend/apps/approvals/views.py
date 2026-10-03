from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from .models import ApprovalChain, ApprovalStep
from .serializers import ApprovalChainSerializer, ApprovalStepSerializer
from .services import compact_steps, reorder_steps

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

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        chain = self.get_object()
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

    def perform_destroy(self, instance):
        chain = instance.approval_chain
        super().perform_destroy(instance)
        compact_steps(chain)  # keep orders 1..n with no gap
