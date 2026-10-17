from django.conf import settings
from django.db import models

from core.models import BaseModel


class AuditLogError(Exception):
    """Raised on any attempt to change or remove a log row."""


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditLogError('The audit log is append-only: rows cannot be updated.')

    def delete(self):
        raise AuditLogError('The audit log is append-only: rows cannot be deleted.')

    def bulk_update(self, objs, fields, batch_size=None):
        raise AuditLogError('The audit log is append-only: rows cannot be updated.')


class AuditLog(BaseModel):
    """
    One row for one sensitive action: who did what, to which record, in which company, and when.
    Append-only: the model refuses update and delete. Field VALUES are never stored (only the names of the
    fields that changed), so the log cannot leak a salary or a password hash.
    """
    ACTION_CHOICES = [
        ('create', 'Created'), ('update', 'Updated'), ('delete', 'Deleted'),
        ('read', 'Read (Break-Glass)'), ('export', 'Exported'), ('denied', 'Refused'),
    ]
    STATUS_CHOICES = [('success', 'Success'), ('warning', 'Warning'), ('failed', 'Failed')]

    # SET_NULL: the row outlives a deleted company, user or employee; the name snapshots below keep it readable.
    company = models.ForeignKey('tenants.Company', null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    company_name = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actor_email = models.CharField(max_length=254, blank=True)   # an email, or a label such as "System (demo data)"
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    module = models.CharField(max_length=50, db_index=True)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['company', 'module']),
        ]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.actor_email} {self.action} {self.model_name}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditLogError('The audit log is append-only: a row cannot be changed.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditLogError('The audit log is append-only: a row cannot be deleted.')
