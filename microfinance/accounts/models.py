from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone_number = PhoneNumberField(unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return self.username


class CustomerProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    employer = models.CharField(max_length=200, blank=True)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = PhoneNumberField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_profiles'

    def __str__(self):
        return f"Customer: {self.user.username}"


class AdminProfile(models.Model):
    ADMIN_TYPE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('loan_manager', 'Loan Manager'),
        ('accountant', 'Accountant'),
        ('support', 'Support Staff'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    admin_type = models.CharField(max_length=20, choices=ADMIN_TYPE_CHOICES, default='support')
    department = models.CharField(max_length=100, blank=True)
    staff_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_profiles'

    def __str__(self):
        return f"Admin: {self.user.username}"


class OTPRequest(models.Model):
    PURPOSE_CHOICES = [
        ('login', 'Login'),
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
        ('transaction', 'Transaction'),
    ]
    phone_number = PhoneNumberField()
    otp_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='login')
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    attempt_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'otp_requests'
        indexes = [
            models.Index(fields=['phone_number', '-created_at']),
            models.Index(fields=['expires_at']),
        ]

    def is_valid(self):
        return not self.is_verified and timezone.now() < self.expires_at

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"OTP for {self.phone_number}"


class OTPVerification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
        ('verified', 'Verified'),
    ]
    otp_request = models.ForeignKey(OTPRequest, on_delete=models.CASCADE, related_name='verifications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message_id = models.CharField(max_length=100, blank=True)
    gateway_response = models.JSONField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'otp_verifications'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['message_id']),
        ]


class DeviceSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_sessions', null=True, blank=True)
    phone_number = PhoneNumberField()
    device_id = models.CharField(max_length=200, blank=True)
    device_name = models.CharField(max_length=200, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    app_version = models.CharField(max_length=20, blank=True)
    fcm_token = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'device_sessions'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['device_id']),
            models.Index(fields=['is_active']),
        ]


class AuthAuditLog(models.Model):
    ACTION_TYPES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('otp_requested', 'OTP Requested'),
        ('otp_verified', 'OTP Verified'),
        ('otp_failed', 'OTP Failed'),
        ('otp_expired', 'OTP Expired'),
        ('logout', 'Logout'),
        ('token_refreshed', 'Token Refreshed'),
        ('password_changed', 'Password Changed'),
        ('account_locked', 'Account Locked'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='auth_audit_logs')
    phone_number = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.TextField(blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auth_audit_logs'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['phone_number', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
        ordering = ['-created_at']