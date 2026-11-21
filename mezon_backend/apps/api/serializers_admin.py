"""Admin panel serializerlari (`/api/v1/admin/*`). Advokatlik siri: ish nomi, hisobot va PDF admin javoblarida yo'q —
faqat metama'lumot (varaq, holat, narx, sana)."""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.accounts.models import AuditEvent, Role, User
from apps.billing import quota
from apps.billing.models import Payment, Plan, Subscription
from apps.cases.models import CaseRun
from apps.doc_builder.models import DocumentTemplate
from apps.lex_corpus.models import SyncRun

from .permissions import is_superadmin


class AdminUserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    plan = serializers.SerializerMethodField(help_text="Joriy tarif kodi (xodim — UNLIMITED)")
    plan_name = serializers.SerializerMethodField()
    cases_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = ["id", "phone_number", "full_name", "role", "role_label", "advocate_license_no", "language", "is_active",
                  "is_staff", "is_superuser", "is_fraud_flagged", "date_joined", "last_login", "registered_ip",
                  "last_login_ip", "plan", "plan_name", "cases_count"]
        read_only_fields = ["id", "phone_number", "language", "is_staff", "is_superuser", "date_joined", "last_login",
                            "registered_ip", "last_login_ip"]

    def get_plan(self, user) -> str:
        return quota.plan_for(user).code

    def get_plan_name(self, user) -> str:
        return quota.plan_for(user).display_name

    def validate(self, attrs):
        request = self.context["request"]
        target: User = self.instance
        if target and target.pk == request.user.pk:   # o'zini bloklash yoki rolini tushirish mumkin emas
            if attrs.get("is_active") is False or attrs.get("role", target.role) != target.role:
                raise serializers.ValidationError(_("Oʻz akkauntingiz rolini yoki holatini oʻzgartirib boʻlmaydi"))
        if attrs.get("role") == Role.SUPERADMIN and not request.user.is_superuser:
            raise serializers.ValidationError({"role": [_("Superadmin rolini faqat Django superuser beradi")]})
        return attrs

    def update(self, instance, validated_data):
        if "role" in validated_data:
            instance.is_staff = validated_data["role"] in (Role.MODERATOR, Role.SUPERADMIN) or instance.is_superuser
        return super().update(instance, validated_data)


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    plan_name = serializers.CharField(source="plan.display_name", read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta:
        model = Subscription
        fields = ["id", "user", "user_phone", "plan_code", "plan_name", "status", "started_at", "expires_at", "source",
                  "payment", "is_current"]
        read_only_fields = fields


class GrantSerializer(serializers.Serializer):
    plan = serializers.SlugRelatedField(slug_field="code", queryset=Plan.objects.filter(is_active=True))
    days = serializers.IntegerField(required=False, min_value=1, max_value=3660, help_text="Bo'sh — tarif muddati")


class AdminCaseSerializer(serializers.ModelSerializer):
    """Ish metama'lumoti (nomi va mazmuni yo'q)."""
    owner_phone = serializers.CharField(source="owner.phone_number", read_only=True, default="")
    cost_usd = serializers.FloatField(read_only=True)

    class Meta:
        model = CaseRun
        fields = ["id", "created_at", "owner", "owner_phone", "category", "status", "pages", "cost_usd", "quota_refunded"]
        read_only_fields = fields


class AdminPlanSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    subscribers = serializers.IntegerField(read_only=True, default=0)
    price_uzs = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, allow_null=True,
                                         required=False)

    class Meta:
        model = Plan
        fields = ["id", "code", "name", "display_name", "price_uzs", "duration_days", "daily_case_limit",
                  "monthly_case_limit", "lifetime_case_limit", "max_pages_per_case", "daily_chat_limit",
                  "lifetime_chat_limit", "daily_template_limit", "lifetime_template_limit", "watermark",
                  "priority_queue", "is_active", "sort_order", "subscribers"]

    def validate_code(self, value):
        if self.instance and value != self.instance.code:   # kod — obunalar va standart tarif nomlari kaliti
            raise serializers.ValidationError(_("Tarif kodini oʻzgartirib boʻlmaydi"))
        return value.strip().upper()


class PaymentSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone_number", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    plan_code = serializers.SlugRelatedField(source="plan", slug_field="code", queryset=Plan.objects.all())
    provider_label = serializers.CharField(source="get_provider_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    amount_uzs = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, min_value=0)

    class Meta:
        model = Payment
        fields = ["id", "user", "user_phone", "user_name", "plan_code", "provider", "provider_label", "amount_uzs",
                  "status", "status_label", "external_id", "created_at", "paid_at"]
        read_only_fields = ["id", "status", "created_at", "paid_at"]


class SyncRunSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    summary = serializers.SerializerMethodField(help_text="Ro'yxatlar o'rniga sonlar")

    class Meta:
        model = SyncRun
        fields = ["id", "started_at", "finished_at", "status", "status_label", "summary", "log"]
        read_only_fields = fields

    def get_summary(self, run) -> dict:
        return {k: (len(v) if isinstance(v, list) else v) for k, v in (run.stats or {}).items()}


class AdminTemplateSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.full_name", read_only=True, default="")

    class Meta:
        model = DocumentTemplate
        fields = ["id", "title", "category", "category_label", "language", "description", "legal_basis", "form_schema",
                  "body", "version", "is_published", "approved_by", "approved_by_name", "approved_at", "created_at",
                  "updated_at"]
        read_only_fields = ["id", "version", "approved_by", "approved_at", "created_at", "updated_at"]

    def validate(self, attrs):
        # Model qoidalari (sxema, matn sintaksisi, sxemada yo'q o'zgaruvchilar) — DocumentTemplate.clean()
        candidate = DocumentTemplate(**{**({f: getattr(self.instance, f) for f in
                                            ("title", "category", "language", "description", "legal_basis",
                                             "form_schema", "body")} if self.instance else {}), **attrs})
        try:
            candidate.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, "error_dict") else {"non_field_errors": e.messages})
        return attrs


class TemplateListItemSerializer(AdminTemplateSerializer):
    class Meta(AdminTemplateSerializer.Meta):
        fields = ["id", "title", "category", "category_label", "language", "version", "is_published", "approved_by_name",
                  "approved_at", "updated_at"]


class AuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default="")
    actor_phone = serializers.CharField(source="actor.phone_number", read_only=True, default="")

    class Meta:
        model = AuditEvent
        fields = ["id", "created_at", "actor", "actor_name", "actor_phone", "action", "target", "details", "ip"]
        read_only_fields = fields


class StaffMeSerializer(serializers.Serializer):
    """Admin ilova uchun: foydalanuvchining admin huquqlari."""
    is_staff_role = serializers.BooleanField()
    is_superadmin = serializers.BooleanField()

    @staticmethod
    def for_user(user) -> dict:
        from .permissions import is_staff_role
        return {"is_staff_role": is_staff_role(user), "is_superadmin": is_superadmin(user)}
