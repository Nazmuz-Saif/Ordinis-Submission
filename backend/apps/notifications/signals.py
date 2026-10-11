"""
Tasks tell nobody about notifications; the notifications app listens instead.
A notification is sent when a task is CREATED for someone, or handed to a different assignee later.
(bulk_create does not send signals, so bulk imports stay quiet.)
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from tasks.models import Task
from .services import notify_task_assigned


@receiver(pre_save, sender=Task, dispatch_uid='notifications_remember_assignee')
def remember_assignee(sender, instance, update_fields=None, **kwargs):
    """Keep the assignee as it was in the database, to see later whether it changed."""
    instance._previous_assignee_id = None
    if instance._state.adding:
        return
    if update_fields is not None and not {'assigned_to', 'assigned_to_id'} & set(update_fields):
        instance._previous_assignee_id = instance.assigned_to_id   # this save cannot change the assignee
        return
    instance._previous_assignee_id = (
        Task.objects.filter(pk=instance.pk).values_list('assigned_to_id', flat=True).first()
    )


@receiver(post_save, sender=Task, dispatch_uid='notifications_task_assigned')
def task_assigned(sender, instance, created, **kwargs):
    if created or instance.assigned_to_id != getattr(instance, '_previous_assignee_id', instance.assigned_to_id):
        notify_task_assigned(instance)
