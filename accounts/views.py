import random
import logging
import requests as http_requests

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile
from .serializers import (
    PhoneSerializer, EmailSerializer,
    PhoneOTPVerifySerializer, EmailOTPVerifySerializer,
    ProfileSerializer, ProfileCreateSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)

# In-memory OTP stores — use Redis in production
PHONE_OTP_STORE = {}
EMAIL_OTP_STORE = {}


def generate_otp():
    return str(random.randint(100000, 999999))


def normalize_phone(phone: str) -> str:
    if phone.startswith('+91'):
        phone = phone[3:]
    elif phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]
    return phone.strip()


def build_tokens(user):
    has_profile = Profile.objects.filter(user=user).exists()
    refresh = RefreshToken.for_user(user)
    return {
        'message': 'OTP verified successfully.',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user_id': user.id,
        'needs_profile_completion': not has_profile,
        'role': user.profile.role if has_profile else None,
    }


# ── Fast2SMS ──────────────────────────────────────────────────────────────────

def send_sms_fast2sms(phone: str, otp: str):
    api_key = getattr(settings, 'FAST2SMS_API_KEY', '')
    if not api_key:
        return False, 'FAST2SMS_API_KEY is not set.'
    try:
        response = http_requests.post(
            'https://www.fast2sms.com/dev/bulkV2',
            json={
                'message': (
                    f'🔐 Marine Basket Store\n'
                    f'===========================\n'
                    f'  Your Login OTP: {otp}\n'
                    f'===========================\n'
                    f'⏱  Valid for 10 minutes only\n'
                    f'🚫 Do NOT share this code\n'
                    f'🐟 Team Marine Basket Store'
                ),
                'language': 'english',
                'route': 'q',
                'numbers': phone,
            },
            headers={'authorization': api_key, 'Content-Type': 'application/json'},
            timeout=10,
        )
        data = response.json()
        logger.info(f"Fast2SMS response for {phone}: {data}")
        if data.get('return') is True:
            return True, None
        msg = data.get('message', '')
        if isinstance(msg, list):
            msg = ' | '.join(msg)
        return False, f"Fast2SMS: {msg}"
    except http_requests.exceptions.Timeout:
        return False, 'Fast2SMS request timed out.'
    except Exception as e:
        return False, str(e)


# ── Email OTP ─────────────────────────────────────────────────────────────────

def send_email_otp(email: str, otp: str):
    use_dummy = getattr(settings, 'USE_DUMMY_OTP', True)
    if use_dummy:
        return True, None
    try:
        html_message = f'''
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f0f7ff;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f7ff;padding:40px 20px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,0.1);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0f4c81,#00b4d8);padding:36px 40px;text-align:center;">
            <div style="font-size:2rem;">🐟</div>
            <h1 style="margin:8px 0 4px;color:#ffffff;font-size:1.5rem;font-weight:800;letter-spacing:-0.5px;">Marine Basket Store</h1>
            <p style="margin:0;color:rgba(255,255,255,0.85);font-size:0.88rem;">Fresh seafood, delivered to your door</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            <p style="margin:0 0 8px;font-size:1rem;color:#475569;font-weight:600;">Hello 👋</p>
            <p style="margin:0 0 28px;font-size:0.95rem;color:#64748b;line-height:1.6;">
              Use the OTP below to securely login to your Marine Basket Store account.
            </p>

            <!-- OTP Box -->
            <div style="background:linear-gradient(135deg,#f0f7ff,#e0f2fe);border:2px dashed #00b4d8;border-radius:16px;padding:28px;text-align:center;margin-bottom:28px;">
              <p style="margin:0 0 8px;font-size:0.78rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.1em;">Your One-Time Password</p>
              <div style="font-size:2.8rem;font-weight:900;letter-spacing:12px;color:#0f4c81;font-family:monospace;">{otp}</div>
              <p style="margin:10px 0 0;font-size:0.82rem;color:#94a3b8;">⏱&nbsp; Valid for <strong>10 minutes</strong> only</p>
            </div>

            <!-- Warning -->
            <div style="background:#fff7ed;border-left:4px solid #f97316;border-radius:8px;padding:14px 16px;margin-bottom:28px;">
              <p style="margin:0;font-size:0.85rem;color:#92400e;">
                🚫 <strong>Never share this OTP</strong> with anyone — including Marine Basket Store staff.
              </p>
            </div>

            <p style="margin:0;font-size:0.85rem;color:#94a3b8;line-height:1.6;">
              If you didn't request this OTP, please ignore this email or contact our support.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:24px 40px;text-align:center;border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:0.78rem;color:#94a3b8;">
              © 2025 Marine Basket Store · This is an automated email, please do not reply.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>'''

        from django.core.mail import EmailMultiAlternatives
        msg_obj = EmailMultiAlternatives(
            subject='🔐 Your Marine Basket Store Login OTP',
            body=(
                f'Marine Basket Store - Login OTP\n'
                f'================================\n'
                f'Your OTP: {otp}\n'
                f'Valid for 10 minutes. Do not share.\n'
                f'================================\n'
                f'If you did not request this, ignore this email.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        msg_obj.attach_alternative(html_message, 'text/html')
        msg_obj.send()
        return True, None
    except Exception as e:
        logger.error(f"Email OTP send failed to {email}: {e}")
        return False, str(e)


# ══════════════════════════════════════════════════════════════════════════════
# PHONE OTP
# ══════════════════════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def send_phone_otp(request):
    serializer = PhoneSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = normalize_phone(serializer.validated_data['phone_number'])
    if len(phone) != 10 or not phone.isdigit():
        return Response({'error': 'Enter a valid 10-digit phone number.'}, status=status.HTTP_400_BAD_REQUEST)

    otp = generate_otp()
    PHONE_OTP_STORE[phone] = otp

    if getattr(settings, 'USE_DUMMY_OTP', True):
        return Response({'message': 'OTP generated (dummy mode).', 'otp': otp}, status=status.HTTP_200_OK)

    success, error = send_sms_fast2sms(phone, otp)
    if not success:
        PHONE_OTP_STORE.pop(phone, None)
        return Response({'error': f'Failed to send SMS. {error}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'message': 'OTP sent to your phone.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_phone_otp(request):
    serializer = PhoneOTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = normalize_phone(serializer.validated_data['phone_number'])
    otp = serializer.validated_data['otp']
    stored = PHONE_OTP_STORE.get(phone)

    if not stored:
        return Response({'error': 'OTP not sent or expired.'}, status=status.HTTP_400_BAD_REQUEST)
    if otp != stored:
        return Response({'error': 'Invalid OTP.'}, status=status.HTTP_401_UNAUTHORIZED)

    full_phone = '+91' + phone
    user, _ = User.objects.get_or_create(
        phone_number=full_phone,
        defaults={'username': full_phone}
    )
    user.otp_verified = True
    user.save()
    del PHONE_OTP_STORE[phone]

    return Response(build_tokens(user), status=status.HTTP_200_OK)


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL OTP
# ══════════════════════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def send_email_otp_view(request):
    serializer = EmailSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].lower()
    otp = generate_otp()
    EMAIL_OTP_STORE[email] = otp

    success, error = send_email_otp(email, otp)
    if not success:
        EMAIL_OTP_STORE.pop(email, None)
        return Response({'error': f'Failed to send email OTP. {error}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if getattr(settings, 'USE_DUMMY_OTP', True):
        return Response({'message': 'OTP generated (dummy mode).', 'otp': otp}, status=status.HTTP_200_OK)

    return Response({'message': 'OTP sent to your email.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_otp(request):
    serializer = EmailOTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email'].lower()
    otp = serializer.validated_data['otp']
    stored = EMAIL_OTP_STORE.get(email)

    if not stored:
        return Response({'error': 'OTP not sent or expired.'}, status=status.HTTP_400_BAD_REQUEST)
    if otp != stored:
        return Response({'error': 'Invalid OTP.'}, status=status.HTTP_401_UNAUTHORIZED)

    user, _ = User.objects.get_or_create(
        email=email,
        defaults={'username': email}
    )
    user.otp_verified = True
    user.save()
    del EMAIL_OTP_STORE[email]

    return Response(build_tokens(user), status=status.HTTP_200_OK)


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method == 'GET':
        try:
            p = Profile.objects.get(user=request.user)
            return Response(ProfileSerializer(p).data)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        if Profile.objects.filter(user=request.user).exists():
            return Response({'error': 'Profile already exists. Use PUT to update.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ProfileCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            request.user.is_profile_complete = True
            request.user.save()
            return Response({'message': 'Profile created successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'PUT':
        try:
            p = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProfileCreateSerializer(p, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile updated successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Token Refresh ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    token = request.data.get('refresh')
    if not token:
        return Response({'error': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        refresh = RefreshToken(token)
        return Response({'access': str(refresh.access_token)})
    except Exception:
        return Response({'error': 'Invalid or expired refresh token.'}, status=status.HTTP_401_UNAUTHORIZED)