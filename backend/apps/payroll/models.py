from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel
from tenants.models import Company


class SalaryStructure(BaseModel):
    """
    The current pay structure of one employee: a base salary plus named allowances.
    Confidential: only users holding the manage_finance Permission may touch it,
    whatever their position in the reporting hierarchy.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='salary_structures')
    employee = models.OneToOneField('organization.Employee', on_delete=models.CASCADE, related_name='salary_structure')
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    # {"House Rent": 8000, "Transport": 2000}  (name -> non-negative amount)
    allowances = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['employee__employee_code']

    def __str__(self):
        return f"Salary structure of {self.employee_id}"
