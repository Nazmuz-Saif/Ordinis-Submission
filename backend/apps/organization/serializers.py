from django.db import transaction
from rest_framework import serializers
from accounts.models import User
from accounts.passwords import make_temporary_password
from accounts.serializers import PROFILE_PHONE
from .models import Department, Designation, Employee
from core.serializer_utils import company_of, scope_queryset
from .services import can_see_private_details, creates_reporting_cycle, get_all_managers


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.CharField(source='head.user.full_name', read_only=True, default='')
    head_email = serializers.CharField(source='head.user.email', read_only=True, default='')
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'company', 'head', 'head_name', 'head_email', 'member_count']
        read_only_fields = ['id', 'company']

    def get_fields(self):
        fields = super().get_fields()
        # The head must be an Employee of the SAME company; another company's id is refused.
        scope_queryset(fields['head'], Employee, company_of(self))
        return fields

    def get_member_count(self, obj):
        total = getattr(obj, 'member_total', None)
        return total if total is not None else obj.employees.count()


class DesignationSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Designation
        fields = ['id', 'title', 'company', 'employee_count']
        read_only_fields = ['id', 'company']

    def get_employee_count(self, obj):
        total = getattr(obj, 'holder_total', None)
        return total if total is not None else obj.employees.count()


class EmployeeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    designation_title = serializers.CharField(source='designation.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    email = serializers.EmailField(write_only=True)
    # Optional: when it is left out the system makes a one-time temporary password (returned once on create).
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, style={'input_type': 'password'})
    # The person's name lives on the User; blank is allowed so old rows and old clients still work.
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    # Private details (D4): written by holders of manage_employees, shown only to those who may see them.
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, validators=[PROFILE_PHONE])
    emergency_contact_phone = serializers.CharField(max_length=30, required=False, allow_blank=True, validators=[PROFILE_PHONE])

    PRIVATE_FIELDS = ('phone', 'address', 'emergency_contact_name', 'emergency_contact_phone', 'joined_on')

    class Meta:
        model = Employee
        fields = [
            'id', 'email', 'user_email', 'full_name', 'password', 'company', 'department', 'department_name',
            'designation', 'designation_title', 'reports_to', 'employee_code',
            'phone', 'address', 'emergency_contact_name', 'emergency_contact_phone', 'joined_on',
        ]
        read_only_fields = ['id', 'company']

    # ---- who sees the private details ----
    def _viewer(self):
        request = self.context.get('request')
        return getattr(getattr(request, 'user', None), 'employee', None) if request else None

    def _viewer_has(self, codename):
        """One lookup per request, not per row."""
        cache = self.context.setdefault('_viewer_has', {})
        if codename not in cache:
            viewer = self._viewer()
            cache[codename] = bool(viewer and viewer.has_permission(codename))
        return cache[codename]

    def can_see_private(self, instance):
        if self.context.get('request') is None:
            return True
        return self._viewer_has('manage_employees')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.can_see_private(instance):
            for name in self.PRIVATE_FIELDS:
                data.pop(name, None)
        temporary = getattr(instance, '_temporary_password', None)
        if temporary:
            data['temporary_password'] = temporary
        return data

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
        password = (validated_data.pop('password', '') or '').strip()
        temporary = None
        if not password:
            temporary = password = make_temporary_password()
        full_name = validated_data.pop('full_name', '').strip()
        company = validated_data.pop('company')
        with transaction.atomic():
            from billing.services import ensure_can_add_employee
            ensure_can_add_employee(company)   # refuses with an "upgrade your plan" message when the plan is full
            user = User.objects.create_user(
                email=email, password=password, company=company, full_name=full_name,
                must_change_password=temporary is not None,
            )
            employee = Employee.objects.create(user=user, company=company, **validated_data)
        employee._temporary_password = temporary   # kept in memory only, to show once in the create response
        return employee


    def update(self, instance, validated_data):
        validated_data.pop('email', None)
        validated_data.pop('password', None)
        full_name = validated_data.pop('full_name', None)
        if full_name is not None:
            instance.user.full_name = full_name.strip()
            instance.user.save(update_fields=['full_name', 'updated_at'])
        return super().update(instance, validated_data)


def _person(employee):
    return {
        'id': str(employee.id),
        'full_name': employee.user.full_name,
        'user_email': employee.user.email,
        'employee_code': employee.employee_code,
        'designation_title': employee.designation.title if employee.designation_id else None,
    }


class EmployeeDetailSerializer(EmployeeSerializer):
    """
    One person's page. Everybody in the company gets the public part (name, designation, department,
    the reporting line). The private part (phone, address, emergency contact, joining date) only the
    person, the managers above them and holders of manage_employees get. Salary lines only manage_finance.
    """
    managers = serializers.SerializerMethodField()
    direct_reports = serializers.SerializerMethodField()

    class Meta(EmployeeSerializer.Meta):
        fields = EmployeeSerializer.Meta.fields + ['managers', 'direct_reports']

    def can_see_private(self, instance):
        viewer = self._viewer()
        if viewer is None:
            return True
        return can_see_private_details(viewer, instance)

    def get_managers(self, obj):
        """The chain above this person, from the direct manager up to the top."""
        return [_person(m) for m in get_all_managers(obj)]

    def get_direct_reports(self, obj):
        reports = obj.direct_reports.select_related('user', 'designation').order_by('employee_code')
        return [_person(r) for r in reports]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['contact_visible'] = self.can_see_private(instance)
        if self._viewer_has('manage_finance'):
            data['salary'] = self._salary(instance)
            data['recent_payslips'] = self._payslips(instance)
        return data

    @staticmethod
    def _salary(instance):
        structure = getattr(instance, 'salary_structure', None)
        if structure is None:
            return None
        return {'base_salary': str(structure.base_salary), 'allowances': structure.allowances}

    @staticmethod
    def _payslips(instance):
        rows = instance.payslips.order_by('-year', '-month')[:3]
        return [{'id': str(p.id), 'year': p.year, 'month': p.month, 'net_amount': str(p.net_amount)} for p in rows]
