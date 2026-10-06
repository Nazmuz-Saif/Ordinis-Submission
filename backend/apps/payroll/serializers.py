from rest_framework import serializers

from .models import SalaryStructure


class SalaryStructureSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(
        source='employee.user.email',
        read_only=True
    )
    employee_code = serializers.CharField(
        source='employee.employee_code',
        read_only=True
    )

    class Meta:
        model = SalaryStructure
        fields = [
            'id',
            'employee',
            'employee_name',
            'employee_code',
            'company',
            'base_salary',
            'allowances',
            'effective_from',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'company',
            'employee_name',
            'employee_code',
            'created_at',
        ]

    def validate_employee(self, employee):
        company = self.context['request'].user.company

        if employee.company_id != company.id:
            raise serializers.ValidationError(
                'Employee does not belong to your company.'
            )

        return employee