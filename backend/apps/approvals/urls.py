from rest_framework.routers import DefaultRouter

from .views import ApprovalChainViewSet, ApprovalStepViewSet

router = DefaultRouter()
router.register('chains', ApprovalChainViewSet, basename='approval-chain')
router.register('steps', ApprovalStepViewSet, basename='approval-step')

urlpatterns = router.urls
