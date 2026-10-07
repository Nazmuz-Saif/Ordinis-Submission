from rest_framework.routers import DefaultRouter

from .views import SalaryStructureViewSet

router = DefaultRouter()
router.register('salary-structures', SalaryStructureViewSet, basename='salary-structure')

urlpatterns = router.urls
