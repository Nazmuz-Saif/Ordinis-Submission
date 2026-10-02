from django.db import models
from core.models import BaseModel
from tenants.models import Company


class Permission(BaseModel):
    """
    System-wide permission (global — NOT company-scoped).
    Every company sees the same set of permissions.

    Example:
        codename="manage_departments"
        name="Manage Departments"
        module="organization"
    """
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    module = models.CharField(
        max_length=50,
        help_text="Grouping key: organization, roles, attendance, payroll, etc."
    )

    class Meta:
        ordering = ['module', 'codename']

    def __str__(self):
        return f"{self.module}.{self.codename}"


class Role(BaseModel):
    """
    Company-scoped role — a named collection of permissions.
    Each company creates its own roles (Admin, HR, etc.).

    When a new company registers, a system-default "Admin" role
    is auto-created with all permissions (is_system_default=True).
    """
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="roles"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system_default = models.BooleanField(default=False)
    permissions = models.ManyToManyField(
        Permission, blank=True, related_name="roles"
    )

    class Meta:
        unique_together = ['company', 'name']

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class EmployeeRole(BaseModel):
    """Assignment of a Role to an Employee (an Employee can hold many Roles)."""
    employee = models.ForeignKey(
        "organization.Employee",
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
        # This model used to live in the organization app. The table keeps its old
        # name so existing databases (and their data) carry over without a table copy.
        db_table = "organization_employeerole"
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "role"],
                name="unique_employee_role_assignment",
            )
        ]

    def __str__(self):
        return f"{self.employee.employee_code} — {self.role.name}"
