"""
Auth Service
Handles authentication operations
"""

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from ..models import User
from .pin_service import PINService


class AuthService:
    """Service for authentication operations"""

    @staticmethod
    def login_with_pin(phone_number, pin):
        """
        Login with phone number and PIN

        Returns:
            dict: {'success': bool, 'tokens': dict, 'user': User}
        """
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return {'success': False, 'message': 'Invalid credentials'}

        is_valid, error = PINService.verify_user_pin(user, pin)
        if not is_valid:
            return {'success': False, 'message': error}

        tokens = AuthService._get_tokens_for_user(user)

        return {
            'success': True,
            'tokens': tokens,
            'user': user
        }

    @staticmethod
    def create_user(phone_number, username=None, pin=None):
        """
        Create new user

        Returns:
            dict: {'success': bool, 'user': User}
        """
        if User.objects.filter(phone_number=phone_number).exists():
            return {'success': False, 'message': 'Phone number already registered'}

        user = User.objects.create_user(
            username=username or phone_number,
            phone_number=phone_number,
        )

        if pin:
            user.pin_hash = PINService.create_hash(pin)
            user.save()

        return {'success': True, 'user': user}

    @staticmethod
    def get_tokens_for_user(user):
        """Get JWT tokens for user"""
        return AuthService._get_tokens_for_user(user)

    @staticmethod
    def _get_tokens_for_user(user):
        """Generate JWT tokens for user"""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }