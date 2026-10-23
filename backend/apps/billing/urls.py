from rest_framework.routers import DefaultRouter

from .views import InvoiceViewSet, PaymentViewSet, PlanViewSet, QuoteViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register('plans', PlanViewSet, basename='billing-plan')
router.register('subscription', SubscriptionViewSet, basename='billing-subscription')
router.register('invoices', InvoiceViewSet, basename='billing-invoice')
router.register('quote', QuoteViewSet, basename='billing-quote')
router.register('payments', PaymentViewSet, basename='billing-payment')
urlpatterns = router.urls
