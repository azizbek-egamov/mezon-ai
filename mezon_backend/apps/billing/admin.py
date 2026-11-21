from django.contrib import admin, messages

from . import quota
from .models import Payment, Plan, Subscription, UsageLog


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """TZ §8.1: barcha limitlar shu yerdan boshqariladi (bo'sh chegara — cheksiz)."""
    list_display = ["code", "name", "price_uzs", "daily_case_limit", "monthly_case_limit", "lifetime_case_limit",
                    "max_pages_per_case", "daily_chat_limit", "lifetime_chat_limit", "priority_queue", "is_active"]
    list_editable = ["price_uzs", "is_active"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "started_at", "expires_at", "source"]
    list_filter = ["plan", "status", "source"]
    search_fields = ["user__phone_number", "user__full_name"]
    raw_id_fields = ["user", "payment"]


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "cases_used", "pages_processed", "chat_questions", "templates_used", "llm_cost_usd"]
    list_filter = ["date"]
    search_fields = ["user__phone_number"]
    readonly_fields = [f.name for f in UsageLog._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "plan", "provider", "amount_uzs", "status", "external_id"]
    list_filter = ["provider", "status"]
    search_fields = ["user__phone_number", "external_id"]
    raw_id_fields = ["user"]
    actions = ["mark_paid"]

    @admin.action(description="To'langan deb belgilash va obunani yoqish")
    def mark_paid(self, request, queryset):
        done = 0
        for payment in queryset.exclude(status=Payment.Status.PAID):
            quota.mark_paid(payment)
            done += 1
        self.message_user(request, f"{done} ta to'lov tasdiqlandi, obuna yoqildi", messages.SUCCESS)
