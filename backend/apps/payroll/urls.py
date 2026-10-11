from rest_framework.routers import DefaultRouter

from .views import PayslipViewSet, SalaryStructureViewSet

router = DefaultRouter()
router.register('salary-structures', SalaryStructureViewSet, basename='salary-structure')
router.register('payslips', PayslipViewSet, basename='payslip')

urlpatterns = router.urls
