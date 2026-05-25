from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'error': response.data,
            'status_code': response.status_code,
        }

    return response


class APIException(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InsufficientBalanceException(APIException):
    def __init__(self):
        super().__init__('Insufficient balance', status_code=400)


class InvalidOTPException(APIException):
    def __init__(self):
        super().__init__('Invalid or expired OTP', status_code=400)


class LoanNotFoundException(APIException):
    def __init__(self):
        super().__init__('Loan not found', status_code=404)