"""
SMS Service
Sends SMS via Android gateway or mock mode
"""

import requests
from django.conf import settings

SMS_TIMEOUT = 30


class SMSService:
    """Service for sending SMS via Android gateway"""

    @staticmethod
    def send(phone, message):
        """Send SMS to phone number"""
        use_mock = getattr(settings, 'USE_MOCK_SMS_GATEWAY', True)
        if use_mock:
            return SMSService._mock_send(phone, message)

        try:
            gateway_url = getattr(settings, 'SMS_GATEWAY_URL', 'http://localhost:8080/send')
            payload = {
                "phone": phone,
                "message": message
            }

            response = requests.post(
                gateway_url,
                json=payload,
                timeout=SMS_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        'success': True,
                        'message': 'SMS sent successfully'
                    }
                else:
                    return {
                        'success': False,
                        'message': data.get('error', 'SMS gateway error')
                    }
            else:
                return {
                    'success': False,
                    'message': f'SMS gateway returned {response.status_code}'
                }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'SMS gateway timeout'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Cannot connect to SMS gateway'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'SMS error: {str(e)}'
            }

    @staticmethod
    def _mock_send(phone, message):
        """Mock SMS sending for development"""
        print(f"[MOCK SMS] To: {phone}, Message: {message}")
        return {
            'success': True,
            'message': 'Mock SMS sent successfully (check console for message)'
        }

    @staticmethod
    def send_otp(phone, otp):
        """Send OTP SMS to phone"""
        message = f"MicroFinance OTP: {otp}\n\nThis code expires in 5 minutes.\nDo not share this code with anyone."
        return SMSService.send(phone, message)