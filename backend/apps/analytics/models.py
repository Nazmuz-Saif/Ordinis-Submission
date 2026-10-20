from django.db import models

from core.models import BaseModel


class CompanyHealthSnapshot(BaseModel):
    """
    One row per company and day: how healthy the company was on that day.
    Written by `python manage.py take_health_snapshots` (run it once a day), never by a page load.
    `health_score` is the average of the attendance rate and the task completion rate.
    """
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, related_name='health_snapshots')
    date = models.DateField()
    headcount = models.PositiveIntegerField(default=0)
    attendance_rate = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    task_completion_rate = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    open_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)
    health_score = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['company', 'date'], name='one_health_snapshot_per_company_per_day'),
            models.CheckConstraint(
                condition=models.Q(attendance_rate__gte=0, attendance_rate__lte=100,
                                   task_completion_rate__gte=0, task_completion_rate__lte=100),
                name='snapshot_rates_0_to_100',
            ),
        ]

    def __str__(self):
        return f'{self.company_id} {self.date} {self.health_score}'
