"""
OTP Service
Handles OTP generation, validation, and rate limiting
"""

from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import status

from ..models import OTPRequest, User
from ..utils import OTPGenerator, PhoneValidator, OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS, OTP_RESEND_LIMIT, OTP_LOCKOUT_MINUTES, OTP_RATE_LIMIT_REQUESTS, OTP_RATE_LIMIT_WINDOW_MINUTES


class OTPService:
    """Service for OTP operations"""

    @staticmethod
    def request_otp(phone_number, purpose='login', ip_address=None):
        """Request a new OTP"""
        is_valid, result = PhoneValidator.validate(phone_number)
        if not is_valid:
            return {'success': False, 'message': result}

        formatted_phone = result

        rate_limited, rate_message = OTPService._check_rate_limit(formatted_phone, ip_address)
        if rate_limited:
            return {'success': False, 'message': rate_message}

        raw_otp = OTPGenerator.generate()
        otp_hash = OTPGenerator.hash(raw_otp)
        expires_at = OTPGenerator.get_expiry()

        recent_otp = OTPRequest.objects.filter(
            phone_number=formatted_phone,
            purpose=purpose,
            is_used=False
        ).order_by('-created_at').first()

        if recent_otp:
            if recent_otp.resend_count >= OTP_RESEND_LIMIT:
                return {
                    'success': False,
                    'message': f'Maximum resend attempts reached. Try again in {OTP_RESEND_LIMIT} minutes.'
                }

            recent_otp.otp_hash = otp_hash
            recent_otp.expires_at = expires_at
            recent_otp.resend_count += 1
            recent_otp.ip_address = ip_address
            recent_otp.save()
            otp_record = recent_otp
        else:
            otp_record = OTPRequest.objects.create(
                phone_number=formatted_phone,
                otp_hash=otp_hash,
                purpose=purpose,
                expires_at=expires_at,
                ip_address=ip_address
            )

        # Send SMS
        from ..services.sms_service import SMSService
        sms_result = SMSService.send_otp(formatted_phone, raw_otp)
        if not sms_result['success']:
            otp_record.delete()
            return {'success': False, 'message': sms_result['message']}

        return {
            'success': True,
            'message': 'OTP sent successfully',
            'expires_at': expires_at.isoformat()
        }

    @staticmethod
    def verify_otp(phone_number, otp, purpose='login'):
        """Verify OTP"""
        is_valid, result = PhoneValidator.validate(phone_number)
        if not is_valid:
            return {'success': False, 'message': result}

        formatted_phone = result

        try:
            otp_record = OTPRequest.objects.filter(
                phone_number=formatted_phone,
                purpose=purpose,
                is_used=False
            ).order_by('-created_at').first()
        except OTPRequest.DoesNotExist:
            return {'success': False, 'message': 'Invalid OTP'}

        if not otp_record:
            return {'success': False, 'message': 'Invalid OTP'}

        if OTPGenerator.is_expired(otp_record.expires_at):
            return {'success': False, 'message': 'OTP has expired'}

        if otp_record.attempts >= OTP_MAX_ATTEMPTS:
            return {
                'success': False,
                'message': f'Too many failed attempts. Try again in {OTP_LOCKOUT_MINUTES} minutes.'
            }

        if not OTPGenerator.verify(otp, otp_record.otp_hash):
            otp_record.attempts += 1
            otp_record.save()
            remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
            return {
                'success': False,
                'message': f'Invalid OTP. {remaining} attempts remaining.'
            }

        otp_record.is_used = True
        otp_record.save()

        user = None
        if purpose == 'login':
            try:
                user = User.objects.get(phone_number=formatted_phone)
            except User.DoesNotExist:
                return {'success': False, 'message': 'Account not found'}
        elif purpose in ['signup', 'reset_pin']:
            try:
                user = User.objects.get(phone_number=formatted_phone)
            except User.DoesNotExist:
                user = None

        return {
            'success': True,
            'message': 'OTP verified successfully',
            'user': user
        }

    @staticmethod
    def _check_rate_limit(phone_number, ip_address):
        """Check rate limiting"""
        window_start = timezone.now() - timedelta(minutes=OTP_RATE_LIMIT_WINDOW_MINUTES)

        phone_count = OTPRequest.objects.filter(
            phone_number=phone_number,
            created_at__gte=window_start
        ).count()

        if phone_count >= OTP_RATE_LIMIT_REQUESTS:
            return True, f'Too many requests. Please wait {OTP_RATE_LIMIT_WINDOW_MINUTES} minutes.'

        if ip_address:
            ip_count = OTPRequest.objects.filter(
                ip_address=ip_address,
                created_at__gte=window_start
            ).count()

            if ip_count >= OTP_RATE_LIMIT_REQUESTS * 2:
                return True, f'Too many requests from this IP.'

        return False, None