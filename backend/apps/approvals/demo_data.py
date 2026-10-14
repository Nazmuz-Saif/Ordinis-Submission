from datetime import timedelta

from rbac.models import Role
from .models import ApprovalChain, ApprovalStep, DelegationRule

ORDER = 30


def wipe(company):
    """A Role cannot be deleted while a step uses it (PROTECT), so the steps go first."""
    ApprovalStep.objects.filter(approval_chain__company=company).delete()


def seed(ctx):
    company = ctx.company
    chain, created = ApprovalChain.objects.get_or_create(
        company=company, name='Leave Approval', defaults={'applies_to_module': 'leave'},
    )
    ctx.note('approval chains', created)
    for order, role_name in enumerate(['Manager', 'HR'], start=1):
        _, created = ApprovalStep.objects.get_or_create(
            approval_chain=chain, step_order=order,
            defaults={'approver_role': Role.objects.get(company=company, name=role_name)},
        )
        ctx.note('approval steps', created)

    _, created = DelegationRule.objects.get_or_create(
        company=company, delegator=ctx.emp('manager'), delegate=ctx.emp('sales_head'),
        defaults={
            'start_date': ctx.today + timedelta(days=2), 'end_date': ctx.today + timedelta(days=6),
            'reason': 'Attending an engineering conference',
        },
    )
    ctx.note('delegations', created)
