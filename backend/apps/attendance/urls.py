from rest_framework.routers import DefaultRouter

from .leave_views import LeaveRequestViewSet, LeaveTypeViewSet
from .views import AttendanceViewSet

router = DefaultRouter()
router.register('attendance', AttendanceViewSet, basename='attendance')
router.register('leave-types', LeaveTypeViewSet, basename='leave-type')
router.register('leave-requests', LeaveRequestViewSet, basename='leave-request')

urlpatterns = router.urls
