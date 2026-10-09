from django.conf import settings
from django.db import models

from core.models import BaseModel
from organization.models import Employee
from tenants.models import Company


class SupportAccessRequest(BaseModel):
    """
    Break-Glass: a Platform Admin asks ONE company for time-limited read access.
    Nothing is readable until the company's CEO approves, and the access ends by itself.
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_DENIED = 'denied'
    STATUS_REVOKED = 'revoked'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DENIED, 'Denied'),
        (STATUS_REVOKED, 'Revoked'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='access_requests')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='support_access_requests',
    )
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    decided_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    decided_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company} / {self.requested_by} ({self.status})'


class ImpersonationLog(BaseModel):
    """One row per use of an approved grant. The company can read its own rows."""
    access_request = models.ForeignKey(SupportAccessRequest, on_delete=models.CASCADE, related_name='logs')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    method = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255)
    detail = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.actor} {self.method} {self.endpoint}'


class SupportTicket(BaseModel):
    """A problem report a company's employee sends to Ordinis support."""
    STATUS_OPEN = 'open'
    STATUS_RESOLVED = 'resolved'
    STATUS_CHOICES = [(STATUS_OPEN, 'Open'), (STATUS_RESOLVED, 'Resolved')]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='support_tickets')
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    subject = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.company}: {self.subject}'


class PlatformActionLog(BaseModel):
    """What Platform Admins did to companies (suspend, activate, resolve a ticket). Kept even if the company is removed."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    company_name = models.CharField(max_length=255)
    action = models.CharField(max_length=40)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.actor} {self.action} {self.company_name}'
