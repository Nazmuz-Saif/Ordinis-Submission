from django.db import models

from core.models import BaseModel
from tenants.models import Company
from organization.models import Employee


class Permission(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    name = models.CharField(max_length=100)
    codename = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "codename"],
                name="unique_company_permission_codename",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.codename})"


class Role(BaseModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_company_role_name",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class EmployeeRole(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employee_roles",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="employee_roles",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "role"],
                name="unique_employee_role",
            )
        ]

    def __str__(self):
        return f"{self.employee} → {self.role}"