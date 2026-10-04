from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/organization/', include('organization.urls')),
    path('api/v1/tenants/', include('tenants.urls')),
    path('api/v1/rbac/', include('rbac.urls')),
    path('api/v1/approvals/', include('approvals.urls')),
    path('api/v1/tasks/', include('tasks.urls')),
]