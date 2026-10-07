from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin
from . import services
from .models import Attendance
from .serializers import AttendanceSerializer


class AttendanceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, AuditLoggingMixin, viewsets.GenericViewSet):
    """
    /api/v1/attendance/attendance/            my own attendance records, newest first
    GET  .../today/                           {"date": ..., "record": {...} or null}  (company-local day)
    POST .../check_in/   POST .../check_out/  once per day each
    Everybody records and sees only their OWN attendance here.
    """
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        return Attendance.objects.filter(employee=self.request.user.employee).select_related('company')

    @action(detail=False, methods=['get'])
    def today(self, request):
        employee = request.user.employee
        today, _ = services.local_today(employee.company)
        record = services.get_today(employee)
        return Response({
            'date': today.isoformat(),
            'record': AttendanceSerializer(record).data if record else None,
        })

    def _run(self, request, service):
        try:
            record = service(request.user.employee)
        except services.AttendanceError as exc:
            raise ValidationError(str(exc))
        self._log('UPDATE', record)
        return Response(AttendanceSerializer(record).data)

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        return self._run(request, services.check_in)

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        return self._run(request, services.check_out)
