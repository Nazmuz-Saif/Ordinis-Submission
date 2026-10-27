from django.db import models
from core.models import BaseModel
from tenants.models import Company


class Department(BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="departments"
    )
    name = models.CharField(max_length=100)
    # The person who leads the Department. Optional; need not be a member of it (same company, checked in the serializer).
    head = models.ForeignKey(
        "organization.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="headed_departments",
    )

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
    # Profile details. The person edits phone, address and emergency contact themselves (auth/profile/).
    phone = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    emergency_contact_name = models.CharField(max_length=100, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=30, blank=True, default="")
    joined_on = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "employee_code"],
                name="unique_employee_code_per_company",
            )
        ]

    @property
    def full_name(self):
        return self.user.full_name

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
