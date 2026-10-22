from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from organization.models import Employee
import re

from .models import Payslip, SalaryStructure
from .services import gross_amount, month_label


class SalaryStructureSerializer(serializers.ModelSerializer):
    employee_email = serializers.CharField(source='employee.user.email', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    gross_amount = serializers.SerializerMethodField()

    class Meta:
        model = SalaryStructure
        fields = [
            'id', 'employee', 'employee_email', 'employee_name', 'employee_code',
            'base_salary', 'allowances', 'gross_amount', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_fields(self):
        fields = super().get_fields()
        scope_queryset(fields['employee'], Employee, company_of(self))
        return fields

    def get_gross_amount(self, obj):
        return str(gross_amount(obj))

    def validate_employee(self, value):
        if self.instance and value != self.instance.employee:
            raise serializers.ValidationError('The employee of a salary structure cannot be changed.')
        return value

    def validate_allowances(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Allowances must be a list of name and amount pairs.')
        clean = {}
        for name, amount in value.items():
            if not str(name).strip():
                raise serializers.ValidationError('Every allowance needs a name.')
            try:
                number = Decimal(str(amount))
            except (InvalidOperation, ValueError):
                raise serializers.ValidationError(f'The amount of "{name}" must be a number.')
            if not number.is_finite() or number < 0:
                raise serializers.ValidationError(f'The amount of "{name}" cannot be negative.')
            clean[str(name).strip()] = float(number) if number % 1 else int(number)
        return clean


MONTH_FORMAT = re.compile(r'^(\d{4})-(0[1-9]|1[0-2])$')


class PayslipSerializer(serializers.ModelSerializer):
    """A payslip as it is shown: the month as YYYY-MM plus a readable label, and the frozen amounts."""
    employee_email = serializers.CharField(source='employee.user.email', read_only=True)
    employee_name = serializers.CharField(source='employee.user.full_name', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    generated_by_email = serializers.SerializerMethodField()
    generated_by_name = serializers.SerializerMethodField()
    month = serializers.SerializerMethodField()
    month_label = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            'id', 'employee', 'employee_email', 'employee_name', 'employee_code', 'month', 'month_label', 'currency',
            'base_salary', 'allowances', 'gross_amount', 'deductions', 'deduction_note', 'net_amount',
            'generated_by_email', 'generated_by_name', 'created_at',
        ]
        read_only_fields = fields

    def get_month(self, obj):
        return f'{obj.year}-{obj.month:02d}'

    def get_month_label(self, obj):
        return month_label(obj.year, obj.month)

    def get_currency(self, obj):
        settings = getattr(obj.company, 'settings', None)
        return settings.currency if settings else 'BDT'

    def get_generated_by_email(self, obj):
        return obj.generated_by.user.email if obj.generated_by else None

    def get_generated_by_name(self, obj):
        return obj.generated_by.user.full_name if obj.generated_by else None


class PayslipGenerateSerializer(serializers.Serializer):
    """What the accountant sends. Only the employee, the month and optional deductions; amounts come from the Salary Structure."""
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    month = serializers.CharField()
    deductions = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, default=0)
    deduction_note = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def get_fields(self):
        fields = super().get_fields()
        scope_queryset(fields['employee'], Employee, company_of(self))
        return fields

    def validate_month(self, value):
        match = MONTH_FORMAT.match(value.strip())
        if not match:
            raise serializers.ValidationError('Use the format YYYY-MM, for example 2026-10.')
        return int(match.group(1)), int(match.group(2))
