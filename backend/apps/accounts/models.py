from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from core.models import BaseModel
from tenants.models import Company
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="users",
        null=True, blank=True,
    )
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # Platform Admin: runs Ordinis itself. Has no company, no Employee, and no default access to any company's data.
    is_platform_admin = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email