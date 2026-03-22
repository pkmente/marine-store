from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from cloudinary.models import CloudinaryField

class UserManager(BaseUserManager):
    def create_user(self, phone_number=None, email=None, username=None, password=None, **extra_fields):
        if not phone_number and not email:
            raise ValueError('Phone number or email is required')
        user = self.model(
            phone_number=phone_number or '',
            email=self.normalize_email(email) if email else '',
            username=username or phone_number or email,
            **extra_fields
        )
        user.set_password(password or self.make_random_password())
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(
            username=username,
            password=password,
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    is_profile_complete = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'
    # Ensure createsuperuser prompts for email so our manager validation passes
    REQUIRED_FIELDS = ['email']
    objects = UserManager()

    def __str__(self):
        return self.phone_number or self.email or self.username


class Profile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('admin', 'Admin'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=150)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    avatar = CloudinaryField('Avatar', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"
