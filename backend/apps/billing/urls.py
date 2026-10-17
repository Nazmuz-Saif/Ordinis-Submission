from rest_framework.routers import DefaultRouter

from .views import InvoiceViewSet, PlanViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register('plans', PlanViewSet, basename='billing-plan')
router.register('subscription', SubscriptionViewSet, basename='billing-subscription')
router.register('invoices', InvoiceViewSet, basename='billing-invoice')
urlpatterns = router.urls
