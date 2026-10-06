from django.urls import path

from .views import AttendanceViewSet


urlpatterns = [
    path(
        'attendance/',
        AttendanceViewSet.as_view({'get': 'list'}),
        name='attendance-list',
    ),

    path(
        'attendance/check_in/',
        AttendanceViewSet.as_view({'post': 'check_in'}),
        name='attendance-check-in',
    ),

    path(
        'attendance/check_out/',
        AttendanceViewSet.as_view({'post': 'check_out'}),
        name='attendance-check-out',
    ),

    path(
        'attendance/history/',
        AttendanceViewSet.as_view({'get': 'history'}),
        name='attendance-history',
    ),
]