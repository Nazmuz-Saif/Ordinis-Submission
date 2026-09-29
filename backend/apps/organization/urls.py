from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet,
    DesignationViewSet,
    EmployeeViewSet,
    EmployeeRoleViewSet,
)

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='department')
router.register('designations', DesignationViewSet, basename='designation')
router.register('employees', EmployeeViewSet, basename='employee')
router.register('employee-roles', EmployeeRoleViewSet, basename='employee-role')


urlpatterns = router.urls