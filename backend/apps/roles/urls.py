from rest_framework.routers import DefaultRouter
from .views import PermissionViewSet, RoleViewSet, EmployeeRoleViewSet

router = DefaultRouter()
router.register('permissions', PermissionViewSet, basename='permission')
router.register('roles', RoleViewSet, basename='role')
router.register('assignments', EmployeeRoleViewSet, basename='employee-role')

urlpatterns = router.urls
