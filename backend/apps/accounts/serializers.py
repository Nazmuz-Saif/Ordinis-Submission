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
    ceo_email = serializers.EmailField()
    ceo_password = serializers.CharField(write_only=True, min_length=8)

    def validate_subdomain(self, value):
        if Company.objects.filter(subdomain=value).exists():
            raise serializers.ValidationError("This subdomain is already taken.")
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

        ceo_designation = Designation.objects.create(company=company, title="CEO")

        user = User.objects.create_user(
            email=validated_data['ceo_email'],
            password=validated_data['ceo_password'],
            company=company,
        )

        employee_code = f"{company.subdomain[:4].upper()}-EMP001"
        employee = Employee.objects.create(
            user=user,
            company=company,
            designation=ceo_designation,
            employee_code=employee_code,
        )

        return {"company": company, "user": user, "employee": employee}