"""
OTP Utilities
"""

import secrets
import hashlib
import string
from datetime import datetime, timedelta

# OTP Settings
OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_LIMIT = 3
OTP_LOCKOUT_MINUTES = 30
OTP_RATE_LIMIT_REQUESTS = 5
OTP_RATE_LIMIT_WINDOW_MINUTES = 5

# PIN Settings
PIN_LENGTH = 6
PIN_MIN_VALUE = 0
PIN_MAX_VALUE = 999999


class OTPGenerator:
    """OTP generation and validation utilities"""

    @staticmethod
    def generate():
        """Generate a random 6-digit OTP"""
        return ''.join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))

    @staticmethod
    def hash(otp):
        """Hash OTP using SHA256 for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()

    @staticmethod
    def verify(raw_otp, stored_hash):
        """Verify OTP against stored hash"""
        return OTPGenerator.hash(raw_otp) == stored_hash

    @staticmethod
    def get_expiry():
        """Get OTP expiration datetime"""
        from django.utils import timezone
        return timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    @staticmethod
    def is_expired(expires_at):
        """Check if OTP has expired"""
        from django.utils import timezone
        return timezone.now() > expires_at


class PINGenerator:
    """PIN generation and validation utilities"""

    @staticmethod
    def hash(pin):
        """Hash PIN using SHA256"""
        return hashlib.sha256(pin.encode()).hexdigest()

    @staticmethod
    def verify(raw_pin, stored_hash):
        """Verify PIN against stored hash"""
        return PINGenerator.hash(raw_pin) == stored_hash

    @staticmethod
    def validate(pin):
        """Validate PIN format (6 digits)"""
        if not pin:
            return False, "PIN is required"

        if not pin.isdigit():
            return False, "PIN must contain only digits"

        if len(pin) != 6:
            return False, "PIN must be 6 digits"

        return True, None


class PhoneValidator:
    """Phone number validation utilities"""

    @staticmethod
    def format(phone):
        """Format phone number to +251XXXXXXXXX format"""
        if not phone:
            return None

        digits = ''.join(filter(str.isdigit, phone))

        if digits.startswith('251'):
            return f'+{digits}'

        if digits.startswith('0'):
            digits = digits[1:]
            return f'+251{digits}'

        if digits.startswith('9') or digits.startswith('7'):
            return f'+251{digits}'

        return f'+{digits}'

    @staticmethod
    def validate(phone):
        """Validate Ethiopian phone number"""
        formatted = PhoneValidator.format(phone)

        if not formatted:
            return False, "Phone number is required"

        digits = formatted[1:]

        if len(digits) != 12:
            return False, "Invalid phone number length"

        if not digits.startswith('251'):
            return False, "Invalid country code"

        return True, formatted