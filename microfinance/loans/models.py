from django.db import models
from django.conf import settings
from django.utils import timezone


class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('active', 'Active'),
        ('paid_off', 'Paid Off'),
        ('defaulted', 'Defaulted'),
    ]
    LOAN_TYPE_CHOICES = [
        ('personal', 'Personal'),
        ('business', 'Business'),
        ('emergency', 'Emergency'),
        ('salary_advance', 'Salary Advance'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='loans')
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPE_CHOICES, default='personal')
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4)
    interest_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    purpose = models.TextField()
    term_months = models.IntegerField()
    monthly_payment = models.DecimalField(max_digits=18, decimal_places=2)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='approved_loans')
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Loan {self.id} - {self.user.username} - {self.amount}"

    def calculate_interest(self):
        self.interest_amount = self.amount * self.interest_rate * (self.term_months / 12)
        self.total_amount = self.amount + self.interest_amount
        self.monthly_payment = self.total_amount / self.term_months

    def is_overdue(self):
        return self.status in ['active', 'disbursed'] and self.due_date < timezone.now().date()


class LoanRepayment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('late', 'Late'),
        ('partial', 'Partial'),
    ]
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    installment_number = models.IntegerField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    principal = models.DecimalField(max_digits=18, decimal_places=2)
    interest = models.DecimalField(max_digits=18, decimal_places=2)
    penalty = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    balance_before = models.DecimalField(max_digits=18, decimal_places=2)
    balance_after = models.DecimalField(max_digits=18, decimal_places=2)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, null=True, blank=True)
    reference_number = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_repayments'
        indexes = [
            models.Index(fields=['loan', 'installment_number']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]
        ordering = ['installment_number']

    def __str__(self):
        return f"Repayment {self.installment_number} - Loan {self.loan.id}"

    def apply_penalty(self):
        if self.status == 'pending' and self.due_date < timezone.now().date():
            from django.conf import settings
            penalty_rate = getattr(settings, 'DEFAULT_PENALTY_RATE', 0.02)
            self.penalty = self.amount * penalty_rate
            self.status = 'late'


class LoanApproval(models.Model):
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ]
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='approvals')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='loan_reviews')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loan_approvals'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - Loan {self.loan.id}"