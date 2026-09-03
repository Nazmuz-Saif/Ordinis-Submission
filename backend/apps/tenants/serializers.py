from rest_framework import serializers
from .models import Company, CompanySettings


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = ['id', 'company', 'currency', 'timezone', 'fiscal_year_start', 'default_language']
        read_only_fields = ['id', 'company']


class CompanySerializer(serializers.ModelSerializer):
    settings = CompanySettingsSerializer(read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'subdomain', 'logo', 'industry', 'is_active', 'settings']
        read_only_fields = ['id', 'is_active']