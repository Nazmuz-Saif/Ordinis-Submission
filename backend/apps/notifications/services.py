"""
Notifications and the Action Inbox.

Notifications are created by the modules where things happen (tasks, approvals) through the
notify_* functions below. The inbox gathers, for ONE employee, everything that needs attention:
approvals waiting for them, tasks they must work on or review, and their unread notifications.
"""
from django.utils import timezone

from approvals.models import ApprovalAction, ApprovalInstance
from approvals.services import can_act, current_step_of, delegators_of, pending_instances_for
from organization.models import Employee
from rbac.models import EmployeeRole
from tasks.models import Task
from .models import Notification

TASKS_LINK = '/tasks'
APPROVALS_LINK = '/approvals/pending'


def notify(recipient, kind, title, message='', link=''):
    """One notification for one employee. Always in the recipient's own company."""
    return Notification.objects.create(
        company_id=recipient.company_id, recipient=recipient, kind=kind,
        title=title[:200], message=message[:500], link=link,
    )


def _name(employee):
    return employee.user.email if employee else 'Someone'


# ---------- Creating notifications ----------

def notify_task_assigned(task):
    """Tell the assignee. Nothing is sent when you give a task to yourself."""
    assignee = task.assigned_to
    if assignee is None or task.assigned_by_id == assignee.id:
        return None
    when = f' Due {task.deadline}.' if task.deadline else ''
    return notify(
        assignee, Notification.KIND_TASK_ASSIGNED, f'New task: {task.title}',
        f'This task was assigned to you.{when}', TASKS_LINK,
    )


def approvers_of(instance):
    """Everyone who may decide the instance's current step right now: role holders and their active delegates."""
    step = current_step_of(instance)
    if step is None:
        return []
    holder_ids = set(EmployeeRole.objects.filter(role_id=step.approver_role_id).values_list('employee_id', flat=True))
    candidate_ids = set(holder_ids)
    from approvals.models import DelegationRule
    today = timezone.localdate()
    candidate_ids |= set(DelegationRule.objects.filter(
        delegator_id__in=holder_ids, start_date__lte=today, end_date__gte=today,
    ).values_list('delegate_id', flat=True))
    candidates = Employee.objects.filter(id__in=candidate_ids, company_id=instance.company_id).select_related('user')
    return [e for e in candidates if can_act(e, instance, step=step)]


def notify_approval_reached(instance):
    """An approval has reached a step: tell everyone who can decide it."""
    who = instance.requested_by
    title = f'Approval needed: {instance.approval_chain.name}'
    message = f'{_name(who)} is waiting for your decision.'
    return [
        notify(e, Notification.KIND_APPROVAL_REQUESTED, title, message, APPROVALS_LINK)
        for e in approvers_of(instance)
    ]


def notify_approval_finished(instance):
    """The request is over (approved or rejected): tell the person who asked."""
    approved = instance.status == ApprovalInstance.STATUS_APPROVED
    return notify(
        instance.requested_by, Notification.KIND_APPROVAL_DECIDED,
        f'{instance.approval_chain.name}: {"approved" if approved else "rejected"}',
        'Your request was approved.' if approved else 'Your request was rejected. Open it to read the comment.',
        APPROVALS_LINK,
    )


# ---------- Reading and marking ----------

def unread_for(employee):
    return Notification.objects.filter(company_id=employee.company_id, recipient=employee, is_read=False)


def mark_read(notification):
    """Idempotent: reading twice changes nothing."""
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at', 'updated_at'])
    return notification


def mark_all_read(employee):
    return unread_for(employee).update(is_read=True, read_at=timezone.now())


# ---------- The Action Inbox ----------

OPEN_TASK_STATUSES = [Task.STATUS_NOT_STARTED, Task.STATUS_IN_PROGRESS, Task.STATUS_REJECTED]
STATUS_LABELS = dict(Task.STATUS_CHOICES)
ORDER = {'approval': 0, 'task_review': 1, 'task': 2, 'notification': 3}


def _item(kind, id_, title, subtitle, link, created_at, overdue=False):
    return {
        'kind': kind, 'id': str(id_), 'title': title, 'subtitle': subtitle, 'link': link,
        'created_at': created_at, 'overdue': overdue,
    }


def inbox_items(employee, today=None):
    """Everything that needs this employee's attention, most urgent group first."""
    if today is None:
        from attendance.services import local_today
        today, _zone = local_today(employee.company)

    items = []
    for inst in pending_instances_for(employee):
        items.append(_item(
            'approval', inst.id, f'Approval needed: {inst.approval_chain.name}',
            f'From {_name(inst.requested_by)}', APPROVALS_LINK, inst.created_at,
        ))

    mine = Task.objects.filter(company_id=employee.company_id, assigned_to=employee, status__in=OPEN_TASK_STATUSES)
    for task in mine.select_related('assigned_by__user'):
        late = bool(task.deadline and task.deadline < today)
        due = f'Due {task.deadline}' if task.deadline else 'No deadline'
        items.append(_item(
            'task', task.id, task.title, f'{STATUS_LABELS[task.status]} · {due}', TASKS_LINK, task.created_at, late,
        ))

    to_review = Task.objects.filter(
        company_id=employee.company_id, assigned_by=employee, status=Task.STATUS_SUBMITTED,
    ).select_related('assigned_to__user')
    for task in to_review:
        items.append(_item(
            'task_review', task.id, f'Review: {task.title}', f'Submitted by {_name(task.assigned_to)}',
            TASKS_LINK, task.updated_at,
        ))

    for note in unread_for(employee):
        items.append(_item('notification', note.id, note.title, note.message, note.link, note.created_at))

    # group order first, then: overdue first, then newest
    items.sort(key=lambda i: (ORDER[i['kind']], not i['overdue'], -i['created_at'].timestamp()))
    return items


def inbox_counts(items):
    counts = {kind: 0 for kind in ORDER}
    for item in items:
        counts[item['kind']] += 1
    return {
        'total': len(items), 'approvals': counts['approval'], 'tasks': counts['task'],
        'reviews': counts['task_review'], 'unread': counts['notification'],
    }
