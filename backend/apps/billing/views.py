from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from rbac.decorators import PermissionRequiredMixin
from . import services
from .models import Invoice, SubscriptionPlan
from .models import PaymentSubmission
from .serializers import InvoiceSerializer, PaymentSerializer, PaymentSubmitSerializer, PlanSerializer


class PlanViewSet(PermissionRequiredMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """The plans a company can be on. The same list for every company, so there is no detail route."""
    serializer_class = PlanSerializer
    permission_required = 'view_billing'
    allow_when_restricted = True      # a restricted company must be able to see its plan and pay
    pagination_class = None

    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True)


class SubscriptionViewSet(PermissionRequiredMixin, viewsets.ViewSet):
    """GET /billing/subscription/: the company's plan and how many of its employee seats are used."""
    permission_required = 'view_billing'
    allow_when_restricted = True

    def list(self, request):
        company = request.user.company
        subscription = services.get_subscription(company)
        return Response({
            'success': True,
            'data': {
                'plan': PlanSerializer(subscription.plan).data,
                'status': subscription.status,
                'started_on': subscription.started_on,
                'timeline': services.subscription_summary(company),
                'usage': services.usage(company),
            },
        })


class InvoiceViewSet(PermissionRequiredMixin, viewsets.ReadOnlyModelViewSet):
    """The company's own invoices, newest month first. Another company's invoice is a 404."""
    serializer_class = InvoiceSerializer
    permission_required = 'view_billing'
    allow_when_restricted = True

    def get_queryset(self):
        queryset = Invoice.objects.filter(company=self.request.user.company)
        status = self.request.query_params.get('status')
        return queryset.filter(status=status) if status else queryset


class QuoteViewSet(PermissionRequiredMixin, viewsets.ViewSet):
    """GET /billing/quote/?plan=<name or id>&months=<1 to 36>: the amount, discount and period. Saves nothing."""
    permission_required = 'view_billing'
    allow_when_restricted = True

    def list(self, request):
        data = services.quote(request.user.company, request.query_params.get('plan'), request.query_params.get('months'))
        return Response({'success': True, 'data': data})


class PaymentViewSet(
    PermissionRequiredMixin, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    /billing/payments/: the company's own payments, newest first, and submitting a new one.
    A company can submit and read, never approve: approving is a Platform Admin action.
    """
    serializer_class = PaymentSerializer
    permission_required = 'manage_billing'
    allow_when_restricted = True      # a restricted company must be able to pay

    def get_queryset(self):
        queryset = PaymentSubmission.objects.filter(company=self.request.user.company).select_related(
            'plan', 'invoice', 'submitted_by__user',
        )
        wanted = self.request.query_params.get('status')
        return queryset.filter(status=wanted) if wanted else queryset

    def create(self, request, *args, **kwargs):
        form = PaymentSubmitSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        d = form.validated_data
        payment = services.submit_payment(
            request.user.employee, plan=d['plan'], months=d['months'], method=d['method'], payer_name=d['payer_name'],
            payer_number=d['payer_number'], transaction_id=d['transaction_id'], expected_amount=d.get('amount'),
        )
        payment = self.get_queryset().get(pk=payment.pk)
        return Response(self.get_serializer(payment).data, status=status.HTTP_201_CREATED)
