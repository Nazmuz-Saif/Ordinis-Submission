from django.db import models

from core.models import BaseModel
from organization.models import Employee


class Attendance(BaseModel):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "date"],
                name="unique_attendance_per_employee_per_day",
            )
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee} - {self.date}"