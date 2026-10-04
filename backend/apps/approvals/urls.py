from rest_framework.routers import DefaultRouter

from .views import ApprovalChainViewSet, ApprovalInstanceViewSet, ApprovalStepViewSet

router = DefaultRouter()
router.register('chains', ApprovalChainViewSet, basename='approval-chain')
router.register('steps', ApprovalStepViewSet, basename='approval-step')
router.register('instances', ApprovalInstanceViewSet, basename='approval-instance')

urlpatterns = router.urls
