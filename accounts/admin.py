from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile
from django.utils.html import format_html

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['phone_number', 'username', 'is_profile_complete', 'otp_verified', 'is_staff']
    list_filter = ['is_staff', 'is_active', 'otp_verified', 'is_profile_complete']
    search_fields = ['phone_number', 'username']
    ordering = ['-created_at']
    fieldsets = (
        (None, {'fields': ('phone_number', 'username', 'password')}),
        ('Status', {'fields': ('otp_verified', 'is_profile_complete', 'is_active', 'is_staff')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'username', 'password1', 'password2'),
        }),
    )


# @admin.register(Profile)
# class ProfileAdmin(admin.ModelAdmin):
#     list_display = ['full_name', 'user', 'role', 'city', 'created_at']
#     list_filter = ['role', 'city']
#     search_fields = ['full_name', 'user__phone_number', 'email']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'role', 'city', 'created_at', 'avatar_preview']

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" />', obj.avatar.url)
        return "No Avatar"