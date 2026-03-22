from django.urls import path
from . import views

urlpatterns = [
    # Phone OTP
    path('send-otp/', views.send_phone_otp, name='send_phone_otp'),
    path('verify-otp/', views.verify_phone_otp, name='verify_phone_otp'),

    # Email OTP
    path('send-email-otp/', views.send_email_otp_view, name='send_email_otp'),
    path('verify-email-otp/', views.verify_email_otp, name='verify_email_otp'),

    # Profile & token
    path('profile/', views.profile, name='profile'),
    path('token/refresh/', views.refresh_token, name='token_refresh'),
]