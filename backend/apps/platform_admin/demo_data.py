from accounts.models import User
from core import demo
from .models import SupportAccessRequest, SupportTicket
from .services import approve, create_request, create_ticket, deny, log_access, revoke, set_ticket_resolved

ORDER = 70


def _admin(ctx):
    email = demo.email(demo.PLATFORM_LOGIN[1])
    admin = User.objects.filter(email=email).first()
    if admin is None:
        admin = User.objects.create_user(email=email, password=demo.PASSWORD, is_platform_admin=True)
        ctx.note('platform admin logins', True)
    return admin


def _access_request(ctx, admin, reason, outcome):
    if SupportAccessRequest.objects.filter(company=ctx.company, reason=reason).exists():
        return
    request = create_request(admin, ctx.company, reason)
    ctx.note('access requests', True)
    ceo = ctx.emp('ceo')
    if outcome == 'denied':
        deny(request, ceo)
    elif outcome == 'revoked':   # approved, used twice, then the CEO ended it
        grant = approve(request, ceo, 24)
        base = f'/api/v1/platform-admin/support/{ctx.company.id}'
        log_access(grant, admin, 'GET', f'{base}/employees/', 'Listed employees')
        log_access(grant, admin, 'GET', f'{base}/payslips/', 'Opened payslips')
        revoke(grant, ceo)


def seed(ctx):
    admin = _admin(ctx)
    for subject, description, resolved in [
        ('Payslip PDF shows the wrong month', 'The March payslip says February at the top.', True),
        ('Cannot find where to add a holiday', 'We could not find the holiday calendar page.', False),
    ]:
        ticket = SupportTicket.objects.filter(company=ctx.company, subject=subject).first()
        if ticket is None:
            ticket = create_ticket(ctx.emp('hr'), subject, description)
            ctx.note('support tickets', True)
        if resolved:
            set_ticket_resolved(admin, ticket, True)

    # Oldest first. The last one stays pending, waiting for the CEO.
    _access_request(ctx, admin, 'Check why the leave balance page is slow', 'revoked')
    _access_request(ctx, admin, 'Look at a payroll rounding report', 'denied')
    _access_request(ctx, admin, 'Investigate the slow payslip page', 'pending')
