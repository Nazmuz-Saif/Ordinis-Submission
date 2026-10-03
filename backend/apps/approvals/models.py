from django.core.validators import MinValueValidator
from django.db import models

from core.models import BaseModel
from tenants.models import Company


class ApprovalChain(BaseModel):
    """
    A company-defined, ordered list of approval steps for one kind of request.
    Example: "Leave Approval" = step 1 Department Head, step 2 HR.
    """
    MODULE_CHOICES = [
        ('leave', 'Leave Request'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='approval_chains')
    name = models.CharField(max_length=100)
    applies_to_module = models.CharField(max_length=50, choices=MODULE_CHOICES)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='unique_approval_chain_name_per_company'),
        ]

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class ApprovalStep(BaseModel):
    """
    One step of a chain. The step is approved by anyone holding `approver_role`.
    """
    approval_chain = models.ForeignKey(ApprovalChain, on_delete=models.CASCADE, related_name='steps')
    step_order = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # PROTECT: a Role that an approval step depends on cannot be deleted.
    approver_role = models.ForeignKey('roles.Role', on_delete=models.PROTECT, related_name='approval_steps')

    class Meta:
        ordering = ['step_order']
        constraints = [
            models.UniqueConstraint(fields=['approval_chain', 'step_order'], name='unique_step_order_per_chain'),
        ]

    def __str__(self):
        return f"{self.approval_chain.name} - step {self.step_order}"
