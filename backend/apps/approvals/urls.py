from rest_framework.routers import DefaultRouter

from .views import (
    ApprovalChainViewSet, ApprovalInstanceViewSet, ApprovalStepViewSet, DelegationRuleViewSet,
)

router = DefaultRouter()
router.register('chains', ApprovalChainViewSet, basename='approval-chain')
router.register('steps', ApprovalStepViewSet, basename='approval-step')
router.register('instances', ApprovalInstanceViewSet, basename='approval-instance')
router.register('delegations', DelegationRuleViewSet, basename='delegation')

urlpatterns = router.urls
