"""
PIN Service
Handles PIN creation and validation
"""

from django.contrib.auth.hashers import check_password, make_password
from ..utils import PINGenerator
from ..constants.otp_constants import PIN_LENGTH


class PINService:
    """Service for PIN operations"""

    @staticmethod
    def create_hash(raw_pin):
        """Create hashed PIN for storage"""
        return PINGenerator.hash(raw_pin)

    @staticmethod
    def verify(raw_pin, stored_hash):
        """Verify PIN against stored hash"""
        return PINGenerator.verify(raw_pin, stored_hash)

    @staticmethod
    def validate(raw_pin):
        """Validate PIN format"""
        return PINGenerator.validate(raw_pin)

    @staticmethod
    def set_user_pin(user, raw_pin):
        """Set user's PIN"""
        is_valid, error = PINService.validate(raw_pin)
        if not is_valid:
            return False, error

        user.pin_hash = PINService.create_hash(raw_pin)
        user.save()
        return True, None

    @staticmethod
    def verify_user_pin(user, raw_pin):
        """Verify user's PIN"""
        if not user.pin_hash:
            return False, "PIN not set"

        return PINService.verify(raw_pin, user.pin_hash), None