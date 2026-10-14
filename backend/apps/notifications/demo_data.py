from django.utils import timezone

from .models import Notification

ORDER = 90   # last: leave and task seeders have already created their notifications through the real flows


def seed(ctx):
    """Older task notifications are read; each person keeps their newest two unread, so the bell is not empty."""
    stale = []
    for employee in ctx.employees.values():
        unread = Notification.objects.filter(
            company=ctx.company, recipient=employee, kind=Notification.KIND_TASK_ASSIGNED, is_read=False,
        ).order_by('-created_at')
        stale += [n.pk for n in unread[2:]]
    if stale:
        Notification.objects.filter(pk__in=stale).update(is_read=True, read_at=timezone.now())
        ctx.note('notifications marked read', True)
