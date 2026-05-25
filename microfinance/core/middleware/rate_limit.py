import logging
import time
from typing import Callable
from django.http import JsonResponse
from django.core.cache import cache

logger = logging.getLogger(__name__)


class RateLimitMixin:
    def get_rate_limit_key(self, request) -> str:
        ip = self.get_client_ip(request)
        return f"rate_limit:{self.endpoint}:{ip}"

    def get_client_ip(self, request) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip


class OTPRequestRateLimiter(RateLimitMixin):
    def __init__(self):
        self.endpoint = 'otp_request'
        self.max_requests = 5
        self.window_seconds = 300

    def check_rate_limit(self, request) -> tuple[bool, dict]:
        key = self.get_rate_limit_key(request)
        client_ip = self.get_client_ip(request)

        current_count = cache.get(key, 0)

        if current_count >= self.max_requests:
            retry_after = cache.ttl(key)
            logger.warning(f"OTP rate limit exceeded for IP: {client_ip}")
            return False, {
                'error': 'Too many OTP requests. Please try again later.',
                'retry_after': retry_after,
                'max_requests': self.max_requests,
            }

        if current_count == 0:
            cache.set(key, 1, timeout=self.window_seconds)
        else:
            cache.incr(key)

        return True, {'remaining': self.max_requests - current_count - 1}


class LoginRateLimiter(RateLimitMixin):
    def __init__(self):
        self.endpoint = 'login'
        self.max_requests = 10
        self.window_seconds = 300

    def check_rate_limit(self, request) -> tuple[bool, dict]:
        phone_number = request.data.get('phone_number', '')
        key = f"login_attempt:{phone_number}"
        client_ip = self.get_client_ip(request)

        failed_attempts = cache.get(key, 0)

        if failed_attempts >= self.max_requests:
            logger.warning(f"Login rate limit exceeded for phone: {phone_number}")
            return False, {
                'error': 'Too many failed login attempts. Please try again later.',
                'max_attempts': self.max_requests,
            }

        return True, {'remaining': self.max_requests - failed_attempts}

    def record_failed_attempt(self, request) -> None:
        phone_number = request.data.get('phone_number', '')
        key = f"login_attempt:{phone_number}"
        current = cache.get(key, 0)
        cache.set(key, current + 1, timeout=300)

    def clear_failed_attempts(self, phone_number: str) -> None:
        key = f"login_attempt:{phone_number}"
        cache.delete(key)


def rate_limit(max_requests: int = 5, window_seconds: int = 300):
    def decorator(view_func: Callable):
        def wrapped(self, request, *args, **kwargs):
            client_ip = request.META.get('REMOTE_ADDR', 'unknown')
            key = f"rate_limit:{view_func.__name__}:{client_ip}"

            current = cache.get(key, 0)

            if current >= max_requests:
                return JsonResponse({
                    'error': f'Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.',
                }, status=429)

            if current == 0:
                cache.set(key, 1, timeout=window_seconds)
            else:
                cache.incr(key)

            return view_func(self, request, *args, **kwargs)

        return wrapped
    return decorator


def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')