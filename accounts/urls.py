from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegistrationView, LoginView,
    UserListView, UserDetailView, ProfileView,
    OTPRequestView, OTPVerifyView, PINLoginView,
)

urlpatterns = [
    # Auth
    path('register/', RegistrationView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('pin-login/', PINLoginView.as_view(), name='pin_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # OTP
    path('otp/request/', OTPRequestView.as_view(), name='otp_request'),
    path('otp/verify/', OTPVerifyView.as_view(), name='otp_verify'),

    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),

    # Users
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
]