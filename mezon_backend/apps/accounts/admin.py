from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import AdminUserCreationForm
from .models import AuditEvent, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = AdminUserCreationForm
    ordering = ["-date_joined"]
    list_display = ["phone_number", "full_name", "role", "is_active", "is_fraud_flagged", "date_joined"]
    list_filter = ["role", "is_active", "is_fraud_flagged", "is_staff"]
    search_fields = ["phone_number", "full_name", "advocate_license_no"]
    readonly_fields = ["date_joined", "last_login", "consents_json", "registered_ip", "last_login_ip"]
    fieldsets = [
        (None, {"fields": ["phone_number", "password"]}),
        ("Shaxs", {"fields": ["full_name", "role", "advocate_license_no", "consents_json"]}),
        ("Holat", {"fields": ["is_active", "is_fraud_flagged", "is_staff", "is_superuser", "groups"]}),
        ("Sanalar", {"fields": ["date_joined", "last_login", "registered_ip", "last_login_ip"]}),
    ]
    add_fieldsets = [(None, {"fields": ["phone_number", "full_name", "role", "password1", "password2"]})]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "action", "target", "ip"]
    list_filter = ["action"]
    search_fields = ["target", "actor__phone_number"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
