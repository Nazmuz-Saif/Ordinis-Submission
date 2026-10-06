
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from .models import Attendance
from .serializers import AttendanceSerializer
from organization.models import Employee
from core.permissions import IsCompanyActive, HasPermission


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsCompanyActive, HasPermission]

    def get_queryset(self):
        employee = self.request.user.employee
        today = timezone.localdate()

        if employee.has_permission('view_attendance'):
            return Attendance.objects.filter(
                employee__company=employee.company,
                date=today,
            ).select_related(
                'employee__user',
                'employee__department',
                'employee__designation',
            )

        return Attendance.objects.filter(
            employee=employee,
            date=today,
        ).select_related(
            'employee__user',
            'employee__department',
            'employee__designation',
        )

    def list(self, request, *args, **kwargs):
        employee = request.user.employee
        today = timezone.localdate()

        if employee.has_permission('view_attendance'):
            employees = Employee.objects.filter(
                company=employee.company
            ).select_related(
                'user',
                'department',
                'designation',
            )

            attendance_records = Attendance.objects.filter(
                employee__company=employee.company,
                date=today,
            ).select_related(
                'employee__user',
                'employee__department',
                'employee__designation',
            )

            attendance_map = {
                record.employee_id: record
                for record in attendance_records
            }

        else:
            employees = Employee.objects.filter(
                id=employee.id
            ).select_related(
                'user',
                'department',
                'designation',
            )

            attendance_map = {
                record.employee_id: record
                for record in Attendance.objects.filter(
                    employee=employee,
                    date=today,
                )
            }

        data = []

        for emp in employees:
            attendance = attendance_map.get(emp.id)

            data.append({
                'id': attendance.id if attendance else None,
                'employee': emp.id,
                'employee_name': emp.user.email,
                'employee_code': emp.employee_code,
                'department_name': (
                    emp.department.name
                    if emp.department
                    else None
                ),
                'designation_name': (
                    emp.designation.title
                    if emp.designation
                    else None
                ),
                'date': today,
                'check_in': (
                    attendance.check_in
                    if attendance
                    else None
                ),
                'check_out': (
                    attendance.check_out
                    if attendance
                    else None
                ),
                'created_at': (
                    attendance.created_at
                    if attendance
                    else None
                ),
            })

        return Response(data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        employee = request.user.employee

        if employee.has_permission('view_attendance'):
            records = Attendance.objects.filter(
                employee__company=employee.company,
            ).select_related(
                'employee__user',
                'employee__department',
                'employee__designation',
            ).order_by('-date', '-check_in')

        else:
            records = Attendance.objects.filter(
                employee=employee,
            ).select_related(
                'employee__user',
                'employee__department',
                'employee__designation',
            ).order_by('-date', '-check_in')

        return Response(
            self.get_serializer(records, many=True).data
        )

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        employee = request.user.employee
        today = timezone.localdate()

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
        )

        if not created and attendance.check_in is not None:
            raise ValidationError(
                'You have already checked in today.'
            )

        attendance.check_in = timezone.now()
        attendance.save(
            update_fields=['check_in', 'updated_at']
        )

        return Response(
            self.get_serializer(attendance).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        employee = request.user.employee
        today = timezone.localdate()

        try:
            attendance = Attendance.objects.get(
                employee=employee,
                date=today,
            )
        except Attendance.DoesNotExist:
            raise ValidationError(
                'You must check in before checking out.'
            )

        if attendance.check_in is None:
            raise ValidationError(
                'You must check in before checking out.'
            )

        if attendance.check_out is not None:
            raise ValidationError(
                'You have already checked out today.'
            )

        now = timezone.now()

        if now < attendance.check_in:
            raise ValidationError(
                'Check-out time cannot be before check-in time.'
            )

        attendance.check_out = now
        attendance.save(
            update_fields=['check_out', 'updated_at']
        )

        return Response(
            self.get_serializer(attendance).data,
            status=status.HTTP_200_OK,
        )