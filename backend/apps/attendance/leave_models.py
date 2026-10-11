from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import F, Q

from core.models import BaseModel
from tenants.models import Company


class LeaveType(BaseModel):
    """A kind of leave a company offers, for example Annual or Sick, and how many days a year it allows."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='leave_types')
    name = models.CharField(max_length=60)
    days_allowed_per_year = models.PositiveSmallIntegerField(validators=[MaxValueValidator(366)], default=0)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['company', 'name'], name='one_leave_type_name_per_company'),
        ]

    def __str__(self):
        return f'{self.name} ({self.days_allowed_per_year} days/year)'


class LeaveRequest(BaseModel):
    """
    One request for leave. It starts Pending. While it is Pending or Approved its days count against the
    balance; a Rejected or Cancelled request gives the days back.
    `days` = calendar days from start_date to end_date, both included.
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'), (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'), (STATUS_CANCELLED, 'Cancelled'),
    ]
    COUNTED = [STATUS_PENDING, STATUS_APPROVED]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='leave_requests')
    employee = models.ForeignKey('organization.Employee', on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='requests')
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.PositiveSmallIntegerField()
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        ordering = ['-start_date', '-created_at']
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=F('start_date')), name='leave_end_not_before_start'),
        ]

    def __str__(self):
        return f'{self.employee_id} {self.start_date}..{self.end_date} ({self.status})'
