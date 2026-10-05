from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Attendance
from .serializers import AttendanceSerializer


class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        employee = self.request.user.employee
        return Attendance.objects.filter(
            employee=employee
        ).select_related('employee__user')

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        employee = request.user.employee
        today = timezone.localdate()

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
        )

        if not created and attendance.check_in is not None:
            raise ValidationError('You have already checked in today.')

        attendance.check_in = timezone.now()
        attendance.save(update_fields=['check_in', 'updated_at'])

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
            raise ValidationError('You must check in before checking out.')

        if attendance.check_in is None:
            raise ValidationError('You must check in before checking out.')

        if attendance.check_out is not None:
            raise ValidationError('You have already checked out today.')

        now = timezone.now()

        if now < attendance.check_in:
            raise ValidationError('Check-out time cannot be before check-in time.')

        attendance.check_out = now
        attendance.save(update_fields=['check_out', 'updated_at'])

        return Response(
            self.get_serializer(attendance).data,
            status=status.HTTP_200_OK,
        )