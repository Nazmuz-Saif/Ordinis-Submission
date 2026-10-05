from django.urls import path

from .views import AttendanceViewSet

urlpatterns = [
    path(
        'attendance/',
        AttendanceViewSet.as_view({'get': 'list'}),
        name='attendance-list',
    ),
    path(
        'attendance/check-in/',
        AttendanceViewSet.as_view({'post': 'check_in'}),
        name='attendance-check-in',
    ),
    path(
        'attendance/check-out/',
        AttendanceViewSet.as_view({'post': 'check_out'}),
        name='attendance-check-out',
    ),
]