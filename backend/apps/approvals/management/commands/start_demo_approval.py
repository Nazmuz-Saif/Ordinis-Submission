from django.core.management.base import BaseCommand, CommandError

from approvals.models import ApprovalChain
from approvals.services import ApprovalError, start_approval
from organization.models import Employee


class Command(BaseCommand):
    help = (
        "DEV ONLY: starts an approval request so the approval screens can be tried "
        "before the Leave module exists. The request's target is the requester's own Employee record."
    )

    def add_arguments(self, parser):
        parser.add_argument('--company', required=True, help='Company subdomain')
        parser.add_argument('--chain', required=True, help='Approval chain name')
        parser.add_argument('--requester', required=True, help='Email of the employee who makes the request')

    def handle(self, *args, **opts):
        try:
            chain = ApprovalChain.objects.get(company__subdomain=opts['company'], name=opts['chain'])
            requester = Employee.objects.get(company=chain.company, user__email=opts['requester'])
        except (ApprovalChain.DoesNotExist, Employee.DoesNotExist) as exc:
            raise CommandError(f'Not found: {exc}')
        try:
            instance = start_approval(requester, chain, requester)
        except ApprovalError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f'Started approval {instance.pk} (step 1 of chain "{chain.name}").'))
