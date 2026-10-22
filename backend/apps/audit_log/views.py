import csv
import datetime
from zoneinfo import ZoneInfo

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import PermissionRequiredMixin
from .models import AuditLog
from .serializers import AuditLogSerializer
from .services import safe_record
from . import context

EXPORT_LIMIT = 50000


def _csv_safe(value):
    """A cell that starts with = + - or @ would run as a formula in a spreadsheet."""
    text = '' if value is None else str(value)
    return "'" + text if text[:1] in ('=', '+', '-', '@') else text


class AuditLogViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    """The company's own audit log. Read-only: there is no way to create, change or delete a row through the API."""
    serializer_class = AuditLogSerializer
    permission_required = 'view_audit_log'

    def get_queryset(self):
        queryset = AuditLog.objects.filter(company=self.request.user.company).select_related('actor')
        return self.filter_rows(queryset)

    def filter_rows(self, queryset):
        params = self.request.query_params
        for name in ('module', 'action', 'status', 'model_name'):
            if params.get(name):
                queryset = queryset.filter(**{name: params[name]})
        if params.get('q'):
            from django.db.models import Q
            queryset = queryset.filter(Q(actor_email__icontains=params['q']) | Q(object_repr__icontains=params['q']))
        for name, lookup in (('date_from', 'created_at__date__gte'), ('date_to', 'created_at__date__lte')):
            if params.get(name):
                try:
                    queryset = queryset.filter(**{lookup: datetime.date.fromisoformat(params[name])})
                except ValueError:
                    pass
        return queryset

    @action(detail=False, methods=['get'])
    def modules(self, request):
        """The modules that appear in this company's log, for the filter list."""
        found = AuditLog.objects.filter(company=request.user.company).values_list('module', flat=True).distinct().order_by('module')
        return Response(list(found))

    @action(detail=False, methods=['get'])
    def export(self, request):
        """The same rows the page shows for the current filters, as a CSV file. The export is itself logged."""
        rows = list(self.get_queryset()[:EXPORT_LIMIT])
        zone = self._zone(request.user.company)
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="audit-log.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date and time', 'User', 'Action', 'Module', 'Record', 'Changed fields', 'Status', 'IP address'])
        for row in rows:
            writer.writerow([
                row.created_at.astimezone(zone).strftime('%Y-%m-%d %H:%M:%S'), _csv_safe(row.actor_email), row.get_action_display(),
                row.module, _csv_safe(f'{row.model_name}: {row.object_repr}' if row.model_name else row.object_repr),
                _csv_safe(', '.join(row.changed_fields)), row.get_status_display(), row.ip_address or '',
            ])
        safe_record(
            company=request.user.company, actor=request.user, actor_email=request.user.email, action='export', status='warning',
            module='audit_log', model_name='AuditLog', object_repr=f'{len(rows)} rows', ip_address=context.client_ip(request),
        )
        return response

    @staticmethod
    def _zone(company):
        try:
            return ZoneInfo(company.settings.timezone)
        except Exception:   # noqa: BLE001
            return ZoneInfo('UTC')
