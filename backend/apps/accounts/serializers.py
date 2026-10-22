from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator

from .passwords import check_new_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import transaction
from tenants.models import Company, CompanySettings
from organization.models import Designation, Employee


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.company and not self.user.company.is_active:
            raise serializers.ValidationError(
                "This company's account is currently suspended."
            )
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['company_id'] = str(user.company_id) if user.company_id else None
        return token

class CompanyRegisterSerializer(serializers.Serializer):
    """
    Single-call company + CEO signup. This is the real onboarding entry
    point -- creates a Company, its default CompanySettings, a CEO
    Designation, the CEO's User account, and their Employee record, all
    inside one transaction so nothing is left half-created.
    """
    company_name = serializers.CharField(max_length=255)
    subdomain = serializers.SlugField(max_length=100)
    industry = serializers.CharField(max_length=100, required=False, allow_blank=True)
    ceo_full_name = serializers.CharField(max_length=150)
    ceo_email = serializers.EmailField()
    ceo_password = serializers.CharField(write_only=True, min_length=8)

    def validate_subdomain(self, value):
        if Company.objects.filter(subdomain=value).exists():
            raise serializers.ValidationError("This subdomain is already taken.")
        return value

    def validate_ceo_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the owner's full name.")
        return value

    def validate_ceo_email(self, value):
        from .models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        from .models import User

        company = Company.objects.create(
            name=validated_data['company_name'],
            subdomain=validated_data['subdomain'],
            industry=validated_data.get('industry', ''),
        )
        CompanySettings.objects.create(company=company)
        from billing.services import start_subscription
        start_subscription(company)   # every new company starts on the Basic plan

        ceo_designation = Designation.objects.create(company=company, title="CEO")

        user = User.objects.create_user(
            email=validated_data['ceo_email'],
            password=validated_data['ceo_password'],
            company=company,
            full_name=validated_data['ceo_full_name'],
        )

        employee_code = f"{company.subdomain[:4].upper()}-EMP001"
        employee = Employee.objects.create(
            user=user,
            company=company,
            designation=ceo_designation,
            employee_code=employee_code,
        )

        from rbac.services import create_ceo_role
        create_ceo_role(company, employee)

        return {"company": company, "user": user, "employee": employee}


PROFILE_PHONE = RegexValidator(r'^[0-9+()\- ]*$', 'Use digits, spaces, + ( ) and - only.')


class ProfileUpdateSerializer(serializers.Serializer):
    """
    What a person may change about themselves. Anything else (email, department, designation,
    manager, Roles, salary, employee code ...) is refused, never silently ignored.
    """
    EMPLOYEE_FIELDS = ('phone', 'address', 'emergency_contact_name', 'emergency_contact_phone')

    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, validators=[PROFILE_PHONE])
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    emergency_contact_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(
        max_length=30, required=False, allow_blank=True, validators=[PROFILE_PHONE],
    )

    def to_internal_value(self, data):
        refused = {
            key: 'This field cannot be changed here.'
            for key in data if key not in self.fields
        }
        if refused:
            raise serializers.ValidationError(refused)
        return super().to_internal_value(data)

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Enter your full name.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        if getattr(user, 'employee', None) is None:
            extra = {key: 'The Platform Admin profile has a name only.' for key in self.EMPLOYEE_FIELDS if key in attrs}
            if extra:
                raise serializers.ValidationError(extra)
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    refresh = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('The current password is not correct.')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        new = attrs['new_password']
        if 'confirm_password' in attrs and attrs['confirm_password'] != new:
            raise serializers.ValidationError({'confirm_password': 'The two new passwords do not match.'})
        if new == attrs['current_password']:
            raise serializers.ValidationError({'new_password': 'Choose a password different from the current one.'})
        try:
            check_new_password(user, new)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)})
        return attrs
