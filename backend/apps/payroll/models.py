from django.db import models

from core.models import BaseModel
from tenants.models import Company
from organization.models import Employee


class SalaryStructure(BaseModel):
    employee = models.OneToOneField(
        Employee,
        on_delete=models.CASCADE,
        related_name="salary_structure",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="salary_structures",
    )
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    allowances = models.JSONField(
        default=dict,
        blank=True,
    )
    effective_from = models.DateField()

    class Meta:
        ordering = ["-effective_from"]

    def __str__(self):
        return f"{self.employee.employee_code} — Salary Structure"