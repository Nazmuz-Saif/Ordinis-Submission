from django.db import models

from core.models import BaseModel


class SubscriptionPlan(BaseModel):
    """A plan a company can be on. `max_employees` empty means unlimited."""
    name = models.CharField(max_length=50, unique=True)
    max_employees = models.PositiveIntegerField(null=True, blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['price_monthly', 'name']
        constraints = [models.CheckConstraint(condition=models.Q(price_monthly__gte=0), name='plan_price_not_negative')]

    def __str__(self):
        return self.name


class Subscription(BaseModel):
    """The plan a company is on now. One per company."""
    STATUS_PENDING_PAYMENT = 'pending_payment'
    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING_PAYMENT, 'Pending payment'), (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expired'), (STATUS_CANCELLED, 'Cancelled'),
    ]

    company = models.OneToOneField('tenants.Company', on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    started_on = models.DateField()
    # The paid period. The last day of the period is `current_period_end`. Days left are NEVER stored:
    # they are computed from this date and the company's own today (billing.services.days_left).
    current_period_start = models.DateField()
    current_period_end = models.DateField()
    billing_months = models.PositiveSmallIntegerField(default=12)
    # Which reminder thresholds (7, 3, 1 days) were already sent in this period; emptied when the period changes.
    reminders_sent = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(current_period_end__gte=models.F('current_period_start')),
                name='subscription_period_end_not_before_start',
            ),
        ]

    def __str__(self):
        return f'{self.company_id}: {self.plan.name}'


class Invoice(BaseModel):
    """A monthly bill. It keeps the amount of that day: a later plan change never alters an old invoice."""
    STATUS_OPEN = 'open'
    STATUS_PAID = 'paid'
    STATUS_VOID = 'void'
    STATUS_CHOICES = [(STATUS_OPEN, 'Open'), (STATUS_PAID, 'Paid'), (STATUS_VOID, 'Void')]

    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='invoices')
    number = models.CharField(max_length=40, unique=True)
    plan_name = models.CharField(max_length=50)
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)
    issued_on = models.DateField()
    due_on = models.DateField()
    paid_on = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=10, blank=True)
    transaction_id = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['-period_start', '-created_at']
        constraints = [
            # The monthly generator relies on this to stay idempotent. An invoice written for an approved payment
            # (it carries a payment method) is exempt: approving a payment must never be blocked by a monthly invoice.
            models.UniqueConstraint(
                fields=['subscription', 'period_start'], condition=models.Q(payment_method=''), name='one_invoice_per_period',
            ),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name='invoice_amount_not_negative'),
        ]

    def __str__(self):
        return self.number


class PaymentSubmission(BaseModel):
    """
    A payment the company made OUTSIDE the system (bKash, Nagad, bank, cash) and reported here. The platform team
    checks it and approves or rejects it. The amount is always the server's quote, never what the client sent.
    `period_start` and `period_end` are filled when it is approved.
    """
    METHOD_BKASH = 'bkash'
    METHOD_NAGAD = 'nagad'
    METHOD_BANK = 'bank'
    METHOD_CASH = 'cash'
    METHOD_CHOICES = [
        (METHOD_BKASH, 'bKash'), (METHOD_NAGAD, 'Nagad'), (METHOD_BANK, 'Bank transfer'), (METHOD_CASH, 'Cash'),
    ]
    KIND_NEW = 'new'
    KIND_RENEWAL = 'renewal'
    KIND_UPGRADE = 'upgrade'
    KIND_CHOICES = [(KIND_NEW, 'New'), (KIND_RENEWAL, 'Renewal'), (KIND_UPGRADE, 'Upgrade')]
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [(STATUS_PENDING, 'Pending'), (STATUS_APPROVED, 'Approved'), (STATUS_REJECTED, 'Rejected')]

    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, related_name='payment_submissions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='payment_submissions')
    months = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    payer_name = models.CharField(max_length=100)
    payer_number = models.CharField(max_length=30)
    transaction_id = models.CharField(max_length=64)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    submitted_by = models.ForeignKey('organization.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=500, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    invoice = models.OneToOneField(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment')

    class Meta:
        ordering = ['-created_at', 'id']
        indexes = [models.Index(fields=['status', 'created_at'])]
        constraints = [
            # A transaction id counts once per method. A rejected submission frees its id (it was never accepted).
            models.UniqueConstraint(
                fields=['method', 'transaction_id'], condition=~models.Q(status='rejected'),
                name='one_live_payment_per_transaction_id',
            ),
            models.UniqueConstraint(
                fields=['company'], condition=models.Q(status='pending'), name='one_pending_payment_per_company',
            ),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='payment_amount_positive'),
            models.CheckConstraint(condition=models.Q(months__gte=1, months__lte=36), name='payment_months_1_to_36'),
        ]

    def __str__(self):
        return f'{self.company_id} {self.method} {self.transaction_id} ({self.status})'
