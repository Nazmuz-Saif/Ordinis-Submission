from django.db import models

from core.models import BaseModel
from tenants.models import Company


class Attendance(BaseModel):
    """
    One row per employee per working day. `date` is the day in the COMPANY's own time
    zone (CompanySettings.timezone); check_in / check_out are exact moments (stored in UTC).
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='attendance_records')
    employee = models.ForeignKey('organization.Employee', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'date'], name='one_attendance_per_employee_per_day'),
        ]

    def __str__(self):
        return f"{self.employee_id} {self.date}"
