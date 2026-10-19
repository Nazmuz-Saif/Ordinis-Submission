from rest_framework import mixins, viewsets
from rest_framework.response import Response

from rbac.decorators import PermissionRequiredMixin
from . import services
from .models import CompanyHealthSnapshot
from .serializers import SnapshotSerializer


class OverviewViewSet(PermissionRequiredMixin, viewsets.ViewSet):
    """GET /analytics/overview/: the numbers and chart data of the user's own company. Read-only."""
    permission_required = 'view_analytics'

    def list(self, request):
        return Response({'success': True, 'data': services.overview(request.user.company)})


class SnapshotViewSet(PermissionRequiredMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET /analytics/snapshots/: the company's own daily health snapshots, newest day first. Read-only."""
    serializer_class = SnapshotSerializer
    permission_required = 'view_analytics'

    def get_queryset(self):
        return CompanyHealthSnapshot.objects.filter(company=self.request.user.company)
