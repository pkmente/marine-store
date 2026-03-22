from rest_framework import serializers
from .models import Profile, User


class PhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PhoneOTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6, min_length=6)


class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)


class ProfileSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'full_name', 'phone_number', 'email', 'address',
                  'city', 'pincode', 'role', 'avatar', 'created_at']
        read_only_fields = ['id', 'phone_number', 'email', 'created_at']


class ProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['full_name', 'address', 'city', 'pincode', 'role']