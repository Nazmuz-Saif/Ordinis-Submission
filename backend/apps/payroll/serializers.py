from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from core.serializer_utils import company_of, scope_queryset
from organization.models import Employee
from .models import SalaryStructure
from .services import gross_amount


class SalaryStructureSerializer(serializers.ModelSerializer):
    employee_email = serializers.CharField(source='employee.user.email', read_only=True)
    employee_code = serializers.CharField(source='employee.employee_code', read_only=True)
    gross_amount = serializers.SerializerMethodField()

    class Meta:
        model = SalaryStructure
        fields = [
            'id', 'employee', 'employee_email', 'employee_code',
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
