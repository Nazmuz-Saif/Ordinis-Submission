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
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [(STATUS_ACTIVE, 'Active'), (STATUS_CANCELLED, 'Cancelled')]

    company = models.OneToOneField('tenants.Company', on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    started_on = models.DateField()

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

    class Meta:
        ordering = ['-period_start', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['subscription', 'period_start'], name='one_invoice_per_period'),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name='invoice_amount_not_negative'),
        ]

    def __str__(self):
        return self.number
