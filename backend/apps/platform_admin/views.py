from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import PermissionRequiredMixin
from core.pagination import OrdinisPagination
from core.permissions import IsPlatformAdmin
from organization.models import Department, Employee
from organization.serializers import DepartmentSerializer, EmployeeSerializer
from tasks.models import Task
from tasks.serializers import TaskSerializer
from . import services
from .models import ImpersonationLog, SupportAccessRequest
from .serializers import AccessRequestCreateSerializer, AccessRequestSerializer, ImpersonationLogSerializer


# ---------- Company side (the CEO) ----------

class CompanyAccessRequestViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    """
    /api/v1/platform-admin/company/access-requests/
    The company reads the requests made about IT and decides. Another company's request is a 404.
    """
    serializer_class = AccessRequestSerializer
    permission_required = {
        'list': 'approve_support_access',
        'retrieve': 'approve_support_access',
        'approve': 'approve_support_access',
        'deny': 'approve_support_access',
        'revoke': 'approve_support_access',
    }

    def get_queryset(self):
        return (
            SupportAccessRequest.objects.filter(company=self.request.user.company)
            .select_related('company', 'requested_by', 'decided_by__user')
            .order_by('-created_at', 'id')
        )

    def _decide(self, fn, *args):
        updated = fn(self.get_object(), self.request.user.employee, *args)
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(services.approve, request.data.get('duration_hours'))

    @action(detail=True, methods=['post'])
    def deny(self, request, pk=None):
        return self._decide(services.deny)

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        return self._decide(services.revoke)


class CompanyAccessLogViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    """/api/v1/platform-admin/company/access-log/ : everything Platform Admins did in THIS company."""
    serializer_class = ImpersonationLogSerializer
    permission_required = {'list': 'approve_support_access', 'retrieve': 'approve_support_access'}

    def get_queryset(self):
        return (
            ImpersonationLog.objects.filter(access_request__company=self.request.user.company)
            .select_related('actor').order_by('-created_at', 'id')
        )


# ---------- Platform Admin side ----------

class PlatformAccessRequestViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet,
):
    """/api/v1/platform-admin/requests/ : a Platform Admin's own requests."""
    permission_classes = [IsPlatformAdmin]
    serializer_class = AccessRequestSerializer

    def get_queryset(self):
        return (
            SupportAccessRequest.objects.filter(requested_by=self.request.user)
            .select_related('company', 'requested_by', 'decided_by__user')
            .order_by('-created_at', 'id')
        )

    def create(self, request, *args, **kwargs):
        form = AccessRequestCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        created = services.create_request(request.user, form.validated_data['company'], form.validated_data['reason'])
        return Response(self.get_serializer(created).data, status=status.HTTP_201_CREATED)


SUPPORT_RESOURCES = {
    'departments': (Department, DepartmentSerializer, 'name'),
    'employees': (Employee, EmployeeSerializer, 'employee_code'),
    'tasks': (Task, TaskSerializer, 'created_at'),
}


class SupportDataView(APIView):
    """
    GET /api/v1/platform-admin/support/<company_id>/<departments|employees|tasks>/
    Read-only. Works ONLY inside an approved, unexpired grant. Every call is logged.
    Salary and payroll data is never offered here.
    """
    permission_classes = [IsPlatformAdmin]

    def get(self, request, company_id, resource):
        if resource not in SUPPORT_RESOURCES:
            return Response({'success': False, 'error': {
                'code': 'SUPPORT_UNKNOWN_RESOURCE', 'message': 'Unknown resource.', 'field_errors': {}}}, status=404)
        grant = services.require_active_grant(request.user, company_id)  # raises 403 when not allowed
        model, serializer_class, order = SUPPORT_RESOURCES[resource]
        queryset = model.objects.filter(company_id=company_id).order_by(order, 'id')

        paginator = OrdinisPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = serializer_class(page, many=True, context={'request': request}).data
        services.log_access(
            grant, request.user, 'GET', request.path,
            f'read {resource} (page {paginator.page.number}, {len(page)} rows)',
        )
        return paginator.get_paginated_response(data)
