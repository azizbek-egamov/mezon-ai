"""Shablonlarni yurist-moderator boshqaradi (TZ §5.1.1): yozadi, sinab ko'radi va tasdiqlaydi."""
from django.contrib import admin, messages
from django.utils import timezone

from apps.accounts.models import Role

from .models import DocumentTemplate


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "language", "version", "is_published", "approved_by", "approved_at"]
    list_filter = ["category", "language", "is_published"]
    search_fields = ["title", "description", "body"]
    readonly_fields = ["version", "approved_by", "approved_at", "created_at", "updated_at"]
    fields = ["title", "category", "language", "description", "legal_basis", "form_schema", "body", "is_published",
              "version", "approved_by", "approved_at", "created_at", "updated_at"]
    actions = ["approve"]

    @admin.action(description="Tanlangan shablonlarni tasdiqlash (joriy versiya)")
    def approve(self, request, queryset):
        if not (request.user.is_superuser or request.user.role in (Role.MODERATOR, Role.SUPERADMIN)):
            self.message_user(request, "Shablonni faqat yurist-moderator tasdiqlay oladi", messages.ERROR)
            return
        n = queryset.update(approved_by=request.user, approved_at=timezone.now(), is_published=True)
        self.message_user(request, f"{n} ta shablon tasdiqlandi", messages.SUCCESS)
