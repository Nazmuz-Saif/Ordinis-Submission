from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Max

from rbac.models import EmployeeRole
from .models import ApprovalAction, ApprovalInstance, ApprovalStep

_OFFSET = 1000  # temporary order values, so the unique (chain, step_order) rule never clashes


def next_step_order(chain):
    """Order number for a new step: last step + 1 (1 for an empty chain)."""
    last = chain.steps.aggregate(m=Max('step_order'))['m']
    return (last or 0) + 1


@transaction.atomic
def _renumber(chain, ordered_steps):
    """Gives the steps the orders 1..n in the given sequence (two passes to avoid unique clashes)."""
    for step in ordered_steps:
        ApprovalStep.objects.filter(pk=step.pk).update(step_order=step.step_order + _OFFSET)
    for position, step in enumerate(ordered_steps, start=1):
        ApprovalStep.objects.filter(pk=step.pk).update(step_order=position)


def compact_steps(chain):
    """After a delete, closes the gap so orders are 1..n again."""
    _renumber(chain, list(chain.steps.order_by('step_order')))


def reorder_steps(chain, step_ids):
    """
    New order = the order of `step_ids`. The list must contain every step of this
    chain exactly once, otherwise ValueError.
    """
    steps = {str(s.id): s for s in chain.steps.all()}
    wanted = [str(i) for i in step_ids]
    if len(wanted) != len(set(wanted)) or set(wanted) != set(steps):
        raise ValueError('step_ids must list every step of this chain exactly once.')
    _renumber(chain, [steps[i] for i in wanted])


# ---------------------------------------------------------------------------
# Running a request through a chain
# ---------------------------------------------------------------------------

class ApprovalError(ValueError):
    """The request cannot be decided (wrong state, own request, empty comment...)."""


class NotAnApprover(PermissionError):
    """The actor does not hold the Role of the current step."""


def chain_has_pending(chain):
    return chain.instances.filter(status=ApprovalInstance.STATUS_PENDING).exists()


def start_approval(target, chain, requested_by):
    """
    Starts the chain for `target` (any model instance, e.g. a LeaveRequest).
    Called by other modules, never directly from the API.
    """
    if chain.company_id != requested_by.company_id:
        raise ApprovalError('The chain belongs to a different company.')
    if not chain.steps.exists():
        raise ApprovalError('This approval chain has no steps yet.')
    return ApprovalInstance.objects.create(
        company_id=chain.company_id,
        approval_chain=chain,
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        requested_by=requested_by,
        current_step=1,
    )


def current_step_of(instance):
    return instance.approval_chain.steps.filter(step_order=instance.current_step).first()


def role_ids_of(employee):
    return set(EmployeeRole.objects.filter(employee=employee).values_list('role_id', flat=True))


def can_act(employee, instance, step=None, role_ids=None):
    """True if `employee` may decide the instance's current step right now."""
    if instance.status != ApprovalInstance.STATUS_PENDING:
        return False
    if instance.requested_by_id == employee.id:
        return False  # nobody approves their own request
    step = step or current_step_of(instance)
    if step is None:
        return False
    # ST-117 (delegation) will extend this check: a delegate may act in place of the role holder.
    roles = role_ids if role_ids is not None else role_ids_of(employee)
    return step.approver_role_id in roles


@transaction.atomic
def decide(instance_id, actor, decision, comment=''):
    """
    Records one decision. Approve moves to the next step (the last approval finishes
    the request); reject ends it immediately. Raises ApprovalError / NotAnApprover.
    """
    instance = (
        ApprovalInstance.objects.select_for_update()
        .select_related('approval_chain')
        .get(pk=instance_id, company_id=actor.company_id)
    )
    comment = (comment or '').strip()

    if instance.status != ApprovalInstance.STATUS_PENDING:
        raise ApprovalError(f'This request is already {instance.status}.')
    if instance.requested_by_id == actor.id:
        raise ApprovalError('You cannot decide your own request.')

    step = current_step_of(instance)
    if step is None:
        raise ApprovalError('The current approval step no longer exists.')
    if step.approver_role_id not in role_ids_of(actor):
        raise NotAnApprover('You do not hold the role required for this step.')
    if decision == ApprovalAction.DECISION_REJECTED and not comment:
        raise ApprovalError('A comment is required when rejecting.')

    ApprovalAction.objects.create(
        instance=instance, step=step, step_order=step.step_order,
        actor=actor, decision=decision, comment=comment,
    )

    if decision == ApprovalAction.DECISION_REJECTED:
        instance.status = ApprovalInstance.STATUS_REJECTED
    else:
        is_last = not instance.approval_chain.steps.filter(step_order__gt=step.step_order).exists()
        if is_last:
            instance.status = ApprovalInstance.STATUS_APPROVED
        else:
            instance.current_step = (
                instance.approval_chain.steps.filter(step_order__gt=step.step_order)
                .order_by('step_order').values_list('step_order', flat=True).first()
            )
    instance.save()
    return instance
