from rest_framework.routers import DefaultRouter
from .views import EmployeeRoleViewSet, PermissionViewSet, RoleViewSet

router = DefaultRouter()
router.register('permissions', PermissionViewSet, basename='permission')
router.register('roles', RoleViewSet, basename='role')
router.register('employee-roles', EmployeeRoleViewSet, basename='employee-role')

urlpatterns = router.urls

