import logging
import uuid
import hashlib
import time
from typing import Optional, Dict, Any
from django.conf import settings
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class SMSGatewayException(Exception):
    def __init__(self, message: str, code: str = 'GATEWAY_ERROR', details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class SMSGatewayService:
    def __init__(self):
        self.base_url = getattr(settings, 'SMS_GATEWAY_URL', 'http://localhost:8000')
        self.api_key = getattr(settings, 'SMS_GATEWAY_API_KEY', '')
        self.timeout = getattr(settings, 'SMS_GATEWAY_TIMEOUT', 30)
        self.max_retries = getattr(settings, 'SMS_GATEWAY_MAX_RETRIES', 3)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'MicroFinance-Django/1.0',
        }
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        normalized_phone = self._normalize_phone(phone_number)

        payload = {
            'phone': normalized_phone,
            'message': message,
            'message_id': str(uuid.uuid4()),
            'timestamp': int(time.time()),
        }

        logger.info(f"Sending SMS to {normalized_phone[:6]}*** via gateway: {self.base_url}")

        try:
            response = self.session.post(
                f"{self.base_url}/api/send-sms",
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"SMS sent successfully. Message ID: {data.get('message_id')}")
                return {
                    'success': True,
                    'message_id': data.get('message_id', payload['message_id']),
                    'gateway_response': data,
                }
            elif response.status_code == 429:
                logger.error("SMS Gateway rate limited")
                raise SMSGatewayException(
                    message="SMS service temporarily unavailable. Please try again later.",
                    code='RATE_LIMITED'
                )
            elif response.status_code == 401:
                logger.error("SMS Gateway authentication failed")
                raise SMSGatewayException(
                    message="SMS service configuration error.",
                    code='AUTH_FAILED'
                )
            else:
                error_data = response.json() if response.content else {}
                logger.error(f"SMS Gateway error: {response.status_code} - {error_data}")
                raise SMSGatewayException(
                    message=error_data.get('error', 'Failed to send SMS'),
                    code='GATEWAY_ERROR',
                    details=error_data
                )

        except requests.exceptions.Timeout:
            logger.error(f"SMS Gateway timeout after {self.timeout}s")
            raise SMSGatewayException(
                message="SMS service timeout. Please try again.",
                code='TIMEOUT'
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"SMS Gateway connection error: {str(e)}")
            raise SMSGatewayException(
                message="Unable to connect to SMS service. Please check your network.",
                code='CONNECTION_ERROR'
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"SMS Gateway request failed: {str(e)}")
            raise SMSGatewayException(
                message=f"SMS service error: {str(e)}",
                code='REQUEST_FAILED'
            )

    def _normalize_phone(self, phone: str) -> str:
        phone = phone.strip().replace(' ', '').replace('-', '').replace('+', '')

        if phone.startswith('251'):
            pass
        elif phone.startswith('0'):
            phone = '251' + phone[1:]
        elif len(phone) == 9 and phone.isdigit():
            phone = '251' + phone
        elif len(phone) == 10 and phone.startswith('9'):
            phone = '251' + phone

        return f"+{phone}"

    def check_balance(self) -> Dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}/api/balance",
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {'error': 'Failed to check balance'}
        except Exception as e:
            logger.error(f"Failed to check SMS balance: {str(e)}")
            return {'error': str(e)}

    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}/api/message/{message_id}/status",
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {'error': 'Failed to get message status'}
        except Exception as e:
            logger.error(f"Failed to get message status: {str(e)}")
            return {'error': str(e)}


class MockSMSGatewayService(SMSGatewayService):
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        logger.info(f"[MOCK] SMS to {phone_number[:6]}***: {message}")
        return {
            'success': True,
            'message_id': f"mock_{uuid.uuid4().hex[:12]}",
            'gateway_response': {'mock': True},
        }


def get_sms_gateway() -> SMSGatewayService:
    use_mock = getattr(settings, 'USE_MOCK_SMS_GATEWAY', True)
    if use_mock:
        return MockSMSGatewayService()
    return SMSGatewayService()