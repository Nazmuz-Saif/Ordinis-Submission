from django.db import models
from core.models import BaseModel
from tenants.models import Company


class Department(BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Designation(BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="designations"
    )
    title = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.title} ({self.company.name})"


class Employee(BaseModel):
    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="employee"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="employees"
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employees"
    )
    designation = models.ForeignKey(
        Designation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employees"
    )
    reports_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="direct_reports"
    )
    employee_code = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "employee_code"],
                name="unique_employee_code_per_company",
            )
        ]

    def __str__(self):
        return f"{self.user.email} — {self.designation}"

    def has_permission(self, codename: str) -> bool:
        """
        Checks whether this employee has a specific permission codename,
        through any of their assigned roles (rbac.EmployeeRole -> Role -> Permission).
        """
        return self.employee_roles.filter(
            role__permissions__codename=codename
        ).exists()
