from django.db.models import ProtectedError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from . import leave_services
from .leave_models import LeaveRequest, LeaveType
from .leave_serializers import LeaveRequestSerializer, LeaveTypeSerializer

MANAGE_TYPES = 'manage_leave_types'


class LeaveTypeViewSet(PermissionRequiredMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """
    /api/v1/attendance/leave-types/
    Everyone in the company can READ the types (to choose one when applying).
    Creating, changing and deleting needs manage_leave_types.
    """
    serializer_class = LeaveTypeSerializer
    permission_required = {
        'create': MANAGE_TYPES, 'update': MANAGE_TYPES, 'partial_update': MANAGE_TYPES, 'destroy': MANAGE_TYPES,
    }

    def get_queryset(self):
        return LeaveType.objects.filter(company=self.request.user.company).order_by('name', 'id')

    def perform_create(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        self._log('CREATE', instance)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            raise ValidationError(
                'This leave type already has leave requests, so it cannot be deleted. Set its days to 0 to stop new requests.'
            )


class LeaveRequestViewSet(
    PermissionRequiredMixin, AuditLoggingMixin, mixins.CreateModelMixin, mixins.ListModelMixin,
    mixins.RetrieveModelMixin, viewsets.GenericViewSet,
):
    """
    /api/v1/attendance/leave-requests/
      POST            apply: {"leave_type", "start_date", "end_date", "reason"}; starts Pending, balance is checked
      GET             MY requests only, newest first (?status=pending)
      POST {id}/cancel/   withdraw one of my Pending requests
      GET  balance/       my balance per leave type (?year=2026)
    Nobody sees another person's requests here. Someone else's request is a 404.
    """
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = (
            LeaveRequest.objects.filter(company=user.company, employee=user.employee)
            .select_related('leave_type')
            .prefetch_related(
                'approvals__approval_chain__steps__approver_role', 'approvals__actions__actor__user',
            )
        )
        wanted = self.request.query_params.get('status')
        if wanted in dict(LeaveRequest.STATUS_CHOICES):
            queryset = queryset.filter(status=wanted)
        return queryset.order_by('-start_date', '-created_at', 'id')

    def create(self, request, *args, **kwargs):
        form = self.get_serializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        leave = leave_services.apply_leave(
            request.user.employee, data['leave_type'], data['start_date'], data['end_date'], data.get('reason', ''),
        )
        self._log('CREATE', leave)
        return Response(self.get_serializer(leave).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        leave = leave_services.cancel_leave(self.get_object())
        self._log('UPDATE', leave)
        return Response(self.get_serializer(leave).data)

    @action(detail=False, methods=['get'])
    def balance(self, request):
        year = request.query_params.get('year')
        if year is not None:
            if not (year.isdigit() and 2000 <= int(year) <= 2100):
                raise ValidationError('The year must be like 2026.')
            year = int(year)
        return Response(leave_services.balance_for(request.user.employee, year))
