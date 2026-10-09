from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CompanyAccessLogViewSet, CompanyAccessRequestViewSet, PlatformAccessRequestViewSet, SupportDataView,
)

router = DefaultRouter()
router.register('company/access-requests', CompanyAccessRequestViewSet, basename='company-access-request')
router.register('company/access-log', CompanyAccessLogViewSet, basename='company-access-log')
router.register('requests', PlatformAccessRequestViewSet, basename='platform-access-request')

urlpatterns = [
    path('support/<uuid:company_id>/<str:resource>/', SupportDataView.as_view(), name='support-data'),
] + router.urls
