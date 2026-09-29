from django.db import models
from core.models import BaseModel
from tenants.models import Company


class Permission(BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="permissions"
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
        Company, on_delete=models.CASCADE, related_name="roles"
    )
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
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
    employee_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.user.email} — {self.designation}"

    def has_permission(self, codename: str) -> bool:
        """
        Checks whether this employee has a specific permission
        through any of their assigned roles.
        """
        return self.employee_roles.filter(
            role__permissions__codename=codename
        ).exists()


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
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="employee_roles",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "role"],
                name="unique_employee_role_assignment",
            )
        ]

    def __str__(self):
        return f"{self.employee.employee_code} — {self.role.name}"