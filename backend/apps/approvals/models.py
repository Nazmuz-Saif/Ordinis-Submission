from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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


class ApprovalInstance(BaseModel):
    """
    One live request travelling through a chain (e.g. a leave request).
    `target` can be any model (generic relation). `current_step` is the step_order
    that must be decided next.
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='approval_instances')
    # PROTECT: a chain with history cannot be deleted.
    approval_chain = models.ForeignKey(ApprovalChain, on_delete=models.PROTECT, related_name='instances')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    target = GenericForeignKey('content_type', 'object_id')
    requested_by = models.ForeignKey('organization.Employee', on_delete=models.CASCADE, related_name='approval_requests')
    current_step = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['company', 'status'])]

    def __str__(self):
        return f"{self.approval_chain.name} #{self.pk} ({self.status})"


class ApprovalAction(BaseModel):
    """One decision (approve/reject) on one step of an instance. Never edited or deleted."""
    DECISION_APPROVED = 'approved'
    DECISION_REJECTED = 'rejected'
    DECISION_CHOICES = [
        (DECISION_APPROVED, 'Approved'),
        (DECISION_REJECTED, 'Rejected'),
    ]

    instance = models.ForeignKey(ApprovalInstance, on_delete=models.CASCADE, related_name='actions')
    step = models.ForeignKey(ApprovalStep, on_delete=models.SET_NULL, null=True, blank=True, related_name='actions')
    step_order = models.PositiveIntegerField()  # snapshot, stays correct even if the step is later removed
    actor = models.ForeignKey('organization.Employee', on_delete=models.CASCADE, related_name='approval_actions')
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            # A step of an instance can be decided only once.
            models.UniqueConstraint(fields=['instance', 'step_order'], name='unique_action_per_step'),
        ]

    def __str__(self):
        return f"{self.instance_id} step {self.step_order}: {self.decision}"


class DelegationRule(BaseModel):
    """
    "While I am away, <delegate> may decide the requests that wait for my roles."
    Active on every day from start_date to end_date, both included.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='delegation_rules')
    delegator = models.ForeignKey('organization.Employee', on_delete=models.CASCADE, related_name='delegations_given')
    delegate = models.ForeignKey('organization.Employee', on_delete=models.CASCADE, related_name='delegations_received')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-start_date']
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F('start_date')), name='delegation_end_not_before_start'),
            models.CheckConstraint(condition=~models.Q(delegator=models.F('delegate')), name='delegation_not_to_self'),
        ]

    def __str__(self):
        return f"{self.delegator_id} -> {self.delegate_id} ({self.start_date}..{self.end_date})"
