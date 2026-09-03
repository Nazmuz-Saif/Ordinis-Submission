from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, CompanySettingsViewSet

router = DefaultRouter()
router.register('company', CompanyViewSet, basename='company')
router.register('settings', CompanySettingsViewSet, basename='companysettings')

urlpatterns = router.urls