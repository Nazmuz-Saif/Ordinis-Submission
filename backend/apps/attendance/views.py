from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin
from organization.models import Employee
from . import services
from .models import Attendance
from .serializers import AttendanceSerializer


class AttendanceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, AuditLoggingMixin, viewsets.GenericViewSet):
    """
    /api/v1/attendance/attendance/            my own attendance records, newest first
    GET  .../today/                           {"date": ..., "record": {...} or null}  (company-local day)
    GET  .../calendar/?month=2026-10          my own month: a status per day and the summary
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

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """GET .../calendar/?month=2026-10: my own month, a status per day and the summary (default: this month)."""
        try:
            data = services.month_calendar(request.user.employee, request.query_params.get('month'))
        except services.AttendanceError as exc:
            raise ValidationError(str(exc))
        return Response(data)

    @action(detail=False, methods=['get'], url_path='team/people')
    def team_people(self, request):
        """GET .../team/people/: the people whose attendance I may open (everybody with view_team_attendance, else my team)."""
        people = services.team_people(request.user.employee)
        return Response({
            'results': [self._person(e) for e in people],
            'whole_company': request.user.employee.has_permission(services.TEAM_PERMISSION),
        })

    @action(detail=False, methods=['get'])
    def team(self, request):
        """
        GET .../team/?employee=<id>&month=2026-10: one person's month, with check-in and check-out times.
        An employee outside my scope, or in another company, answers 404 (not 403): it must not reveal who exists.
        """
        employee_id = request.query_params.get('employee')
        if not employee_id:
            raise ValidationError('Choose an employee.')
        try:
            target = services.team_scope(request.user.employee).select_related('user', 'designation', 'department').get(pk=employee_id)
        except (Employee.DoesNotExist, DjangoValidationError, ValueError):
            raise NotFound('Employee not found.')
        try:
            data = services.team_month(target, request.query_params.get('month'))
        except services.AttendanceError as exc:
            raise ValidationError(str(exc))
        data['employee'] = self._person(target)
        return Response(data)

    @staticmethod
    def _person(employee):
        return {
            'id': str(employee.id),
            'full_name': employee.user.full_name,
            'user_email': employee.user.email,
            'employee_code': employee.employee_code,
            'designation_title': employee.designation.title if employee.designation_id else None,
            'department_name': employee.department.name if employee.department_id else None,
        }

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
