from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from .models import User, AuthAuditLog
from .serializers import (
    RegistrationSerializer, LoginSerializer, OTPRequestSerializer,
    OTPVerifySerializer, PasswordResetSerializer, UserSerializer,
    CustomerProfileSerializer, AdminProfileSerializer
)
from .services import get_otp_service, OTPServiceException
from ..middleware.rate_limit import get_client_ip


class RegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            AuthAuditLog.objects.create(
                user=user,
                phone_number=str(user.phone_number),
                action='login_success',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
            )

            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)

            AuthAuditLog.objects.create(
                user=user,
                phone_number=str(user.phone_number),
                action='login_success',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
            )

            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RequestOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = str(serializer.validated_data['phone_number'])
        purpose = serializer.validated_data.get('purpose', 'login')
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        device_info = f"{request.META.get('HTTP_USER_AGENT', 'Unknown')[:200]}"

        try:
            otp_service = get_otp_service()
            result = otp_service.request_otp(
                phone_number=phone_number,
                purpose=purpose,
                ip_address=ip_address,
                device_info=device_info,
            )

            return Response({
                'message': result['message'],
                'otp_id': result.get('otp_id'),
                'expires_at': result.get('expires_at'),
            }, status=status.HTTP_200_OK)

        except OTPServiceException as e:
            return Response(
                {'error': e.message, 'code': e.code},
                status=status.HTTP_429_TOO_MANY_REQUESTS if e.code == 'RATE_LIMITED' else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to send OTP. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = str(serializer.validated_data['phone_number'])
        otp_code = serializer.validated_data['otp_code']
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device_info = f"{request.META.get('HTTP_USER_AGENT', 'Unknown')[:200]}"

        try:
            otp_service = get_otp_service()
            result = otp_service.verify_otp(
                phone_number=phone_number,
                otp_code=otp_code,
                ip_address=ip_address,
                device_info=device_info,
            )

            try:
                user = User.objects.get(phone_number=phone_number)
                user.is_verified = True
                user.save()
                refresh = RefreshToken.for_user(user)

                AuthAuditLog.objects.create(
                    user=user,
                    phone_number=phone_number,
                    action='otp_verified',
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True,
                )

                return Response({
                    'user': UserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Phone number verified successfully'
                }, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({
                    'message': 'OTP verified. Please complete registration.',
                    'verified_phone': phone_number,
                }, status=status.HTTP_200_OK)

        except OTPServiceException as e:
            AuthAuditLog.objects.create(
                phone_number=phone_number,
                action='otp_failed',
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason=e.message,
            )

            status_code = status.HTTP_400_BAD_REQUEST
            if e.code == 'OTP_EXPIRED':
                status_code = status.HTTP_410_GONE
            elif e.code == 'PHONE_LOCKED':
                status_code = status.HTTP_423_LOCKED
            elif e.code == 'MAX_ATTEMPTS_REACHED':
                status_code = status.HTTP_423_LOCKED

            return Response(
                {'error': e.message, 'code': e.code},
                status=status_code
            )
        except Exception as e:
            return Response(
                {'error': 'Verification failed. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone_number = request.data.get('phone_number')

        if not phone_number:
            return Response(
                {'error': 'Phone number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        device_info = f"{request.META.get('HTTP_USER_AGENT', 'Unknown')[:200]}"

        try:
            otp_service = get_otp_service()
            result = otp_service.resend_otp(
                phone_number=phone_number,
                ip_address=ip_address,
                device_info=device_info,
            )

            return Response({
                'message': result['message'],
                'otp_id': result.get('otp_id'),
                'expires_at': result.get('expires_at'),
            }, status=status.HTTP_200_OK)

        except OTPServiceException as e:
            return Response(
                {'error': e.message, 'code': e.code},
                status=status.HTTP_429_TOO_MANY_REQUESTS if e.code in ['RATE_LIMITED', 'PHONE_LOCKED'] else status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to resend OTP. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OTPStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        phone_number = request.query_params.get('phone_number')

        if not phone_number:
            return Response(
                {'error': 'Phone number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_service = get_otp_service()
        status_info = otp_service.get_otp_status(phone_number)

        return Response(status_info, status=status.HTTP_200_OK)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(phone_number=phone_number)
                user.set_password(new_password)
                user.save()

                AuthAuditLog.objects.create(
                    user=user,
                    phone_number=str(phone_number),
                    action='password_changed',
                    ip_address=get_client_ip(request),
                    success=True,
                )

                return Response({'message': 'Password reset successfully'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == 'customer':
            profile = user.customer_profile
            serializer = CustomerProfileSerializer(profile)
        else:
            profile = user.admin_profile
            serializer = AdminProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        if user.role == 'customer':
            profile = user.customer_profile
            serializer = CustomerProfileSerializer(profile, data=request.data, partial=True)
        else:
            profile = user.admin_profile
            serializer = AdminProfileSerializer(profile, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        role = self.request.query_params.get('role')
        queryset = User.objects.all()
        if role:
            queryset = queryset.filter(role=role)
        return queryset


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = UserSerializer