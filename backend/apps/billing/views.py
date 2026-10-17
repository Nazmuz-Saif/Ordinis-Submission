from rest_framework import mixins, viewsets
from rest_framework.response import Response

from rbac.decorators import PermissionRequiredMixin
from . import services
from .models import Invoice, SubscriptionPlan
from .serializers import InvoiceSerializer, PlanSerializer


class PlanViewSet(PermissionRequiredMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """The plans a company can be on. The same list for every company, so there is no detail route."""
    serializer_class = PlanSerializer
    permission_required = 'view_billing'
    pagination_class = None

    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True)


class SubscriptionViewSet(PermissionRequiredMixin, viewsets.ViewSet):
    """GET /billing/subscription/: the company's plan and how many of its employee seats are used."""
    permission_required = 'view_billing'

    def list(self, request):
        company = request.user.company
        subscription = services.get_subscription(company)
        return Response({
            'success': True,
            'data': {
                'plan': PlanSerializer(subscription.plan).data,
                'status': subscription.status,
                'started_on': subscription.started_on,
                'usage': services.usage(company),
            },
        })


class InvoiceViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    """The company's own invoices, newest month first. Another company's invoice is a 404."""
    serializer_class = InvoiceSerializer
    permission_required = 'view_billing'

    def get_queryset(self):
        queryset = Invoice.objects.filter(company=self.request.user.company)
        status = self.request.query_params.get('status')
        return queryset.filter(status=status) if status else queryset
