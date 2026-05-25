import logging
import secrets
import hashlib
from datetime import timedelta
from typing import Optional, Dict, Tuple
from django.utils import timezone
from django.conf import settings
from phonenumber_field.phonenumber import to_python

from ..models import OTPRequest, OTPVerification, DeviceSession, AuthAuditLog
from .sms_gateway_service import get_sms_gateway, SMSGatewayException

logger = logging.getLogger(__name__)


class OTPServiceException(Exception):
    def __init__(self, message: str, code: str = 'OTP_ERROR'):
        self.message = message
        self.code = code
        super().__init__(self.message)


class OTPService:
    def __init__(self):
        self.otp_length = getattr(settings, 'OTP_LENGTH', 6)
        self.otp_expiry_seconds = getattr(settings, 'OTP_EXPIRATION_SECONDS', 300)
        self.max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
        self.resend_limit = getattr(settings, 'OTP_RESEND_LIMIT', 3)
        self.resend_window_minutes = getattr(settings, 'OTP_RESEND_WINDOW_MINUTES', 5)
        self.lockout_minutes = getattr(settings, 'OTP_LOCKOUT_MINUTES', 30)

    def generate_otp(self) -> str:
        return ''.join([str(secrets.randbelow(10)) for _ in range(self.otp_length)])

    def hash_otp(self, otp: str) -> str:
        return hashlib.sha256(otp.encode()).hexdigest()

    def normalize_phone(self, phone_number: str) -> Optional[str]:
        try:
            phone = to_python(phone_number)
            if phone and phone.is_valid():
                return str(phone)
        except Exception:
            pass
        return None

    def request_otp(
        self,
        phone_number: str,
        purpose: str = 'login',
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> Dict[str, any]:
        normalized_phone = self.normalize_phone(phone_number)
        if not normalized_phone:
            raise OTPServiceException("Invalid phone number format", code='INVALID_PHONE')

        if self._is_phone_locked(normalized_phone):
            raise OTPServiceException(
                f"Too many failed attempts. Please try again later.",
                code='PHONE_LOCKED'
            )

        recent_otps = OTPRequest.objects.filter(
            phone_number=normalized_phone,
            created_at__gte=timezone.now() - timedelta(minutes=self.resend_window_minutes)
        ).count()

        if recent_otps >= self.resend_limit:
            raise OTPServiceException(
                f"Maximum OTP requests ({self.resend_limit}) reached. Please try again later.",
                code='RATE_LIMITED'
            )

        otp_code = self.generate_otp()
        otp_hash = self.hash_otp(otp_code)
        expires_at = timezone.now() + timedelta(seconds=self.otp_expiry_seconds)

        otp_request = OTPRequest.objects.create(
            phone_number=normalized_phone,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
            ip_address=ip_address,
            device_info=device_info or '',
        )

        message = f"Your verification code is: {otp_code}\nThis code expires in {self.otp_expiry_seconds // 60} minutes."

        try:
            gateway = get_sms_gateway()
            result = gateway.send_sms(normalized_phone, message)

            OTPVerification.objects.create(
                otp_request=otp_request,
                status='sent',
                message_id=result.get('message_id'),
                gateway_response=result.get('gateway_response'),
                sent_at=timezone.now(),
            )

            AuthAuditLog.objects.create(
                phone_number=normalized_phone,
                action='otp_requested',
                ip_address=ip_address,
                device_info=device_info,
                success=True,
                metadata={'purpose': purpose, 'message_id': result.get('message_id')},
            )

            logger.info(f"OTP sent successfully to {normalized_phone[:6]}***")

            return {
                'success': True,
                'otp_id': otp_request.id,
                'expires_at': expires_at.isoformat(),
                'message': 'OTP sent successfully',
            }

        except SMSGatewayException as e:
            otp_request.delete()
            AuthAuditLog.objects.create(
                phone_number=normalized_phone,
                action='otp_requested',
                ip_address=ip_address,
                device_info=device_info,
                success=False,
                failure_reason=f"SMS Gateway Error: {e.message}",
            )
            logger.error(f"Failed to send OTP: {e.message}")
            raise OTPServiceException(e.message, code=e.code)

        except Exception as e:
            otp_request.delete()
            logger.error(f"Unexpected error sending OTP: {str(e)}")
            raise OTPServiceException("Failed to send OTP. Please try again.", code='SEND_FAILED')

    def verify_otp(
        self,
        phone_number: str,
        otp_code: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> Dict[str, any]:
        normalized_phone = self.normalize_phone(phone_number)
        if not normalized_phone:
            raise OTPServiceException("Invalid phone number format", code='INVALID_PHONE')

        if self._is_phone_locked(normalized_phone):
            raise OTPServiceException(
                "Account temporarily locked due to too many failed attempts.",
                code='PHONE_LOCKED'
            )

        otp_request = OTPRequest.objects.filter(
            phone_number=normalized_phone,
            is_verified=False,
        ).order_by('-created_at').first()

        if not otp_request:
            AuthAuditLog.objects.create(
                phone_number=normalized_phone,
                action='otp_failed',
                ip_address=ip_address,
                device_info=device_info,
                success=False,
                failure_reason='No pending OTP found',
            )
            raise OTPServiceException("No pending OTP found. Please request a new one.", code='NO_OTP')

        if otp_request.is_expired():
            otp_request.is_verified = False
            otp_request.save()

            OTPVerification.objects.create(
                otp_request=otp_request,
                status='expired',
            )

            AuthAuditLog.objects.create(
                phone_number=normalized_phone,
                action='otp_expired',
                ip_address=ip_address,
                device_info=device_info,
                success=False,
            )

            raise OTPServiceException("OTP has expired. Please request a new one.", code='OTP_EXPIRED')

        otp_request.attempt_count += 1

        if otp_request.attempt_count >= self.max_attempts:
            otp_request.is_verified = False
            otp_request.save()

            OTPVerification.objects.create(
                otp_request=otp_request,
                status='failed',
                failure_reason=f'Maximum attempts ({self.max_attempts}) reached',
            )

            self._lock_phone(normalized_phone)

            AuthAuditLog.objects.create(
                phone_number=normalized_phone,
                action='otp_failed',
                ip_address=ip_address,
                device_info=device_info,
                success=False,
                failure_reason=f'Maximum attempts reached. Phone locked for {self.lockout_minutes} minutes.',
            )

            raise OTPServiceException(
                f"Too many failed attempts. Phone locked for {self.lockout_minutes} minutes.",
                code='MAX_ATTEMPTS_REACHED'
            )

        if not self._verify_otp_code(otp_code, otp_request.otp_hash):
            otp_request.save()

            AuthAuditLog.objects.create(
                phone_number=normalized_phone,
                action='otp_failed',
                ip_address=ip_address,
                device_info=device_info,
                success=False,
                failure_reason=f'Invalid OTP. Attempt {otp_request.attempt_count}/{self.max_attempts}',
                metadata={'attempts_remaining': self.max_attempts - otp_request.attempt_count},
            )

            raise OTPServiceException(
                f"Invalid OTP. {self.max_attempts - otp_request.attempt_count} attempts remaining.",
                code='INVALID_OTP'
            )

        otp_request.is_verified = True
        otp_request.save()

        OTPVerification.objects.create(
            otp_request=otp_request,
            status='verified',
        )

        AuthAuditLog.objects.create(
            phone_number=normalized_phone,
            action='otp_verified',
            ip_address=ip_address,
            device_info=device_info,
            success=True,
            metadata={'otp_id': otp_request.id},
        )

        logger.info(f"OTP verified successfully for {normalized_phone[:6]}***")

        return {
            'success': True,
            'message': 'OTP verified successfully',
            'phone_number': normalized_phone,
        }

    def _verify_otp_code(self, input_otp: str, stored_hash: str) -> bool:
        input_hash = self.hash_otp(input_otp)
        return secrets.compare_digest(input_hash, stored_hash)

    def _is_phone_locked(self, phone_number: str) -> bool:
        from django.core.cache import cache
        lock_key = f"otp_lock_{phone_number}"
        return cache.get(lock_key) is not None

    def _lock_phone(self, phone_number: str) -> None:
        from django.core.cache import cache
        lock_key = f"otp_lock_{phone_number}"
        cache.set(lock_key, True, timeout=self.lockout_minutes * 60)
        logger.warning(f"Phone {phone_number[:6]}*** locked for {self.lockout_minutes} minutes")

    def resend_otp(
        self,
        phone_number: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> Dict[str, any]:
        return self.request_otp(
            phone_number=phone_number,
            purpose='resend',
            ip_address=ip_address,
            device_info=device_info,
        )

    def get_otp_status(self, phone_number: str) -> Dict[str, any]:
        normalized_phone = self.normalize_phone(phone_number)
        if not normalized_phone:
            return {'status': 'invalid_phone'}

        latest_otp = OTPRequest.objects.filter(
            phone_number=normalized_phone,
        ).order_by('-created_at').first()

        if not latest_otp:
            return {'status': 'no_otp'}

        if latest_otp.is_verified:
            return {'status': 'verified', 'verified_at': latest_otp.updated_at.isoformat()}

        if latest_otp.is_expired():
            return {'status': 'expired', 'expired_at': latest_otp.expires_at.isoformat()}

        return {
            'status': 'pending',
            'created_at': latest_otp.created_at.isoformat(),
            'expires_at': latest_otp.expires_at.isoformat(),
            'attempts_remaining': self.max_attempts - latest_otp.attempt_count,
        }


def get_otp_service() -> OTPService:
    return OTPService()