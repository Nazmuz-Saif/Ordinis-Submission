from django.db import models
from core.models import BaseModel


class Company(BaseModel):
    name = models.CharField(max_length=255)
    subdomain = models.SlugField(max_length=100, unique=True)
    logo = models.URLField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CompanySettings(BaseModel):
    company = models.OneToOneField(
        Company, on_delete=models.CASCADE, related_name="settings"
    )
    currency = models.CharField(max_length=10, default="BDT")
    timezone = models.CharField(max_length=50, default="Asia/Dhaka")
    fiscal_year_start = models.CharField(max_length=10, default="01-01")
    default_language = models.CharField(max_length=10, default="en")

    def __str__(self):
        return f"Settings for {self.company.name}"