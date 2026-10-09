from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminAccessRequestViewSet, AdminActionLogViewSet, AdminCompanyViewSet, AdminTicketViewSet,
    CompanyAccessLogViewSet, CompanyAccessRequestViewSet, CompanyTicketViewSet,
    PlatformAccessRequestViewSet, SupportDataView,
)

router = DefaultRouter()
# a company's side
router.register('company/access-requests', CompanyAccessRequestViewSet, basename='company-access-request')
router.register('company/access-log', CompanyAccessLogViewSet, basename='company-access-log')
router.register('company/tickets', CompanyTicketViewSet, basename='company-ticket')
# a Platform Admin's side
router.register('requests', PlatformAccessRequestViewSet, basename='platform-access-request')
router.register('admin/companies', AdminCompanyViewSet, basename='admin-company')
router.register('admin/tickets', AdminTicketViewSet, basename='admin-ticket')
router.register('admin/access-requests', AdminAccessRequestViewSet, basename='admin-access-request')
router.register('admin/actions', AdminActionLogViewSet, basename='admin-action')

urlpatterns = [
    path('support/<uuid:company_id>/<str:resource>/', SupportDataView.as_view(), name='support-data'),
] + router.urls
