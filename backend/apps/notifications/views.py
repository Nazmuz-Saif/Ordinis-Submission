from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsCompanyActive
from . import services
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    /api/v1/notifications/
      GET  /                  my notifications (?unread=true for the unread ones)
      POST {id}/read/         mark one read (reading twice is fine)
      POST read-all/          mark all of mine read
      GET  inbox/             my Action Inbox: approvals waiting, tasks to do or review, unread notifications
      GET  inbox/summary/     the counts for the bell
    Only ever MY items: another user's notification (or another company's) is a 404.
    """
    permission_classes = [IsCompanyActive]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        employee = self.request.user.employee
        queryset = Notification.objects.filter(company_id=employee.company_id, recipient=employee)
        if self.request.query_params.get('unread') in ('1', 'true', 'True'):
            queryset = queryset.filter(is_read=False)
        return queryset.order_by('-created_at', 'id')

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        return Response(self.get_serializer(services.mark_read(self.get_object())).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        return Response({'marked': services.mark_all_read(request.user.employee)})

    @action(detail=False, methods=['get'])
    def inbox(self, request):
        items = services.inbox_items(request.user.employee)
        page = self.paginate_queryset(items)
        return self.get_paginated_response(page)

    @action(detail=False, methods=['get'], url_path='inbox/summary')
    def inbox_summary(self, request):
        return Response(services.inbox_counts(services.inbox_items(request.user.employee)))
