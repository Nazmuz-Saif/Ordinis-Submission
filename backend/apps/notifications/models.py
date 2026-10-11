from django.db import models

from core.models import BaseModel
from organization.models import Employee
from tenants.models import Company


class Notification(BaseModel):
    """
    One message for ONE employee ("you were assigned a task", "an approval needs you").
    `link` is the page it opens (a path inside the app, for example /approvals/pending).
    """
    KIND_TASK_ASSIGNED = 'task_assigned'
    KIND_APPROVAL_REQUESTED = 'approval_requested'
    KIND_APPROVAL_DECIDED = 'approval_decided'
    KIND_CHOICES = [
        (KIND_TASK_ASSIGNED, 'Task assigned'),
        (KIND_APPROVAL_REQUESTED, 'Approval requested'),
        (KIND_APPROVAL_DECIDED, 'Approval decided'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='notifications')
    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    message = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f'{self.recipient}: {self.title}'
