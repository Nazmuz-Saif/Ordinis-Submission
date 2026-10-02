from django.db import transaction
from rest_framework import serializers
from accounts.models import User
from .models import Department, Designation, Employee
from core.serializer_utils import company_of, scope_queryset
from .services import creates_reporting_cycle


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'company']
        read_only_fields = ['id', 'company']


class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Designation
        fields = ['id', 'title', 'company']
        read_only_fields = ['id', 'company']


class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_title = serializers.CharField(source='designation.title', read_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Employee
        fields = [
            'id', 'email', 'password', 'company', 'department', 'department_name',
            'designation', 'designation_title', 'reports_to', 'employee_code',
        ]
        read_only_fields = ['id', 'company']

    def get_fields(self):
        fields = super().get_fields()
        company = company_of(self)
        # A client can only link to Departments/Designations/Managers of its own company.
        scope_queryset(fields['department'], Department, company)
        scope_queryset(fields['designation'], Designation, company)
        scope_queryset(fields['reports_to'], Employee, company)
        if self.instance is not None:
            # Email/password are only needed to create the login account.
            fields['email'].required = False
            fields['password'].required = False
        return fields

    def validate_employee_code(self, value):
        # Unique inside the user's own company only; never reveals other companies' codes.
        company = company_of(self)
        taken = Employee.objects.filter(company=company, employee_code=value)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError('This employee code is already used in your company.')
        return value

    def validate(self, attrs):
        manager = attrs.get('reports_to')
        if manager is not None and self.instance is not None:
            if manager.id == self.instance.id:
                raise serializers.ValidationError({'reports_to': 'An employee cannot report to themselves.'})
            if creates_reporting_cycle(self.instance, manager):
                raise serializers.ValidationError({'reports_to': 'This would create a circular reporting chain.'})
        return attrs

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        company = validated_data.pop('company')
        with transaction.atomic():
            user = User.objects.create_user(email=email, password=password, company=company)
            employee = Employee.objects.create(user=user, company=company, **validated_data)
        return employee

    def update(self, instance, validated_data):
        validated_data.pop('email', None)
        validated_data.pop('password', None)
        return super().update(instance, validated_data)
