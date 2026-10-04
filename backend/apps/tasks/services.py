from .models import Task

# Allowed status changes. Anything not listed here is rejected.
ALLOWED_TRANSITIONS = {
    Task.STATUS_NOT_STARTED: {Task.STATUS_IN_PROGRESS},
    Task.STATUS_IN_PROGRESS: {Task.STATUS_SUBMITTED},
    Task.STATUS_SUBMITTED: {Task.STATUS_COMPLETED, Task.STATUS_REJECTED},
    Task.STATUS_REJECTED: {Task.STATUS_IN_PROGRESS},
    Task.STATUS_COMPLETED: set(),
}

_LABELS = dict(Task.STATUS_CHOICES)


class TaskError(ValueError):
    """The requested status change is not allowed."""


class NotTheAssignee(PermissionError):
    """Only the person the task is assigned to may do this."""


def check_transition(current, new):
    if new not in ALLOWED_TRANSITIONS.get(current, set()):
        raise TaskError(f'A task cannot move from {_LABELS[current]} to {_LABELS[new]}.')


def _assignee_changes_status(task, actor, new_status):
    if task.assigned_to_id != actor.id:
        raise NotTheAssignee('Only the assignee can do this.')
    check_transition(task.status, new_status)
    task.status = new_status
    task.save(update_fields=['status', 'updated_at'])
    return task


def start_task(task, actor):
    """Assignee starts working: Not Started (or Rejected) -> In Progress."""
    return _assignee_changes_status(task, actor, Task.STATUS_IN_PROGRESS)


def submit_task(task, actor):
    """Assignee hands the work in: In Progress -> Submitted."""
    return _assignee_changes_status(task, actor, Task.STATUS_SUBMITTED)
