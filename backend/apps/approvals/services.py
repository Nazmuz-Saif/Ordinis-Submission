from django.db import transaction
from django.db.models import Max

from .models import ApprovalStep

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
