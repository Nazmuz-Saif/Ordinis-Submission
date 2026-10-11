from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

from core.mixins import AuditLoggingMixin, PermissionRequiredMixin
from .models import Payslip, SalaryStructure
from .serializers import MONTH_FORMAT, PayslipGenerateSerializer, PayslipSerializer, SalaryStructureSerializer
from .services import generate_payslip

FINANCE = 'manage_finance'


class SalaryStructureViewSet(PermissionRequiredMixin, AuditLoggingMixin, viewsets.ModelViewSet):
    """
    /api/v1/payroll/salary-structures/
    Every action (reading too) needs manage_finance. There is NO hierarchy rule here on
    purpose: a manager above the Accountant gets nothing unless he holds the Permission.
    """
    serializer_class = SalaryStructureSerializer

    permission_required = {
        'list': FINANCE,
        'retrieve': FINANCE,
        'create': FINANCE,
        'update': FINANCE,
        'partial_update': FINANCE,
        'destroy': FINANCE,
    }

    def get_queryset(self):
        return SalaryStructure.objects.filter(
            company=self.request.user.company
        ).select_related('employee__user')

    def perform_create(self, serializer):
        instance = serializer.save(company=self.request.user.company)
        self._log('CREATE', instance)


class PayslipViewSet(
    PermissionRequiredMixin, AuditLoggingMixin, mixins.CreateModelMixin, mixins.ListModelMixin,
    mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet,
):
    """
    /api/v1/payroll/payslips/
      POST     generate one (needs manage_finance): {"employee", "month": "2026-10", "deductions"?, "deduction_note"?}
      GET      finance sees the whole company, EVERYONE ELSE sees only their own (?mine=true: only mine, for finance too)
      DELETE   void a payslip so the month can be generated again (needs manage_finance)
    A payslip is never edited. No hierarchy rule: a manager does not see a subordinate's payslip.
    Someone else's payslip is a 404, not a 403.
    """
    serializer_class = PayslipSerializer

    permission_required = {'create': FINANCE, 'destroy': FINANCE}

    def get_queryset(self):
        user = self.request.user
        employee = user.employee
        queryset = Payslip.objects.filter(company=user.company).select_related('employee__user', 'generated_by__user')
        params = self.request.query_params
        if params.get('mine') in ('1', 'true', 'True') or not employee.has_permission(FINANCE):
            return queryset.filter(employee=employee)
        if params.get('employee'):
            queryset = queryset.filter(employee_id=params['employee'])
        match = MONTH_FORMAT.match(params.get('month') or '')
        if match:
            queryset = queryset.filter(year=int(match.group(1)), month=int(match.group(2)))
        return queryset

    def create(self, request, *args, **kwargs):
        form = PayslipGenerateSerializer(data=request.data, context=self.get_serializer_context())
        form.is_valid(raise_exception=True)
        data = form.validated_data
        year, month = data['month']
        payslip = generate_payslip(
            request.user.employee, data['employee'], year, month, data['deductions'], data['deduction_note'],
        )
        self._log('CREATE', payslip)
        return Response(self.get_serializer(payslip).data, status=status.HTTP_201_CREATED)
