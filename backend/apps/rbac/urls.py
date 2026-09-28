from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PermissionViewSet,
    RoleViewSet,
    EmployeeRoleViewSet,
)


router = DefaultRouter()

router.register(
    "permissions",
    PermissionViewSet,
    basename="permission",
)

router.register(
    "roles",
    RoleViewSet,
    basename="role",
)

router.register(
    "employee-roles",
    EmployeeRoleViewSet,
    basename="employee-role",
)


urlpatterns = [
    path("", include(router.urls)),
]
