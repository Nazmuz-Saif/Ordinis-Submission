from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

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


class Payslip(BaseModel):
    """
    One employee's pay for one month. A SNAPSHOT: the amounts are copied from the Salary Structure when the
    payslip is generated, so changing the Salary Structure later never changes a payslip already issued.
    Exactly one per employee and month, and the database enforces it.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='payslips')
    employee = models.ForeignKey('organization.Employee', on_delete=models.CASCADE, related_name='payslips')
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    allowances = models.JSONField(default=dict, blank=True)
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deduction_note = models.CharField(max_length=255, blank=True)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    generated_by = models.ForeignKey(
        'organization.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )

    class Meta:
        ordering = ['-year', '-month', 'employee__employee_code']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'year', 'month'], name='one_payslip_per_employee_month'),
            models.CheckConstraint(condition=Q(month__gte=1, month__lte=12), name='payslip_month_1_to_12'),
            models.CheckConstraint(condition=Q(deductions__gte=0), name='payslip_deductions_not_negative'),
            models.CheckConstraint(condition=Q(deductions__lte=F('gross_amount')), name='payslip_deductions_within_gross'),
        ]

    def __str__(self):
        return f'Payslip {self.year}-{self.month:02d} of {self.employee_id}'
