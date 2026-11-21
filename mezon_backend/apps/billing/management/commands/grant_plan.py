"""Foydalanuvchiga tarifni qo'lda berish (to'lov tizimi ulanguncha; dev akkauntlar uchun).

    python manage.py grant_plan +998901234567 PRO_MONTHLY [--days 30]
    python manage.py grant_plan --list          # tariflar
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import normalize_phone
from apps.billing import quota
from apps.billing.models import Plan


class Command(BaseCommand):
    help = "Foydalanuvchiga tarif beradi."

    def add_arguments(self, parser):
        parser.add_argument("phone", nargs="?")
        parser.add_argument("plan", nargs="?")
        parser.add_argument("--days", type=int)
        parser.add_argument("--list", action="store_true")

    def handle(self, *args, phone, plan, days, list, **opts):
        for code, fields in quota.DEFAULT_PLANS.items():  # tariflar bo'lmasa (yangi baza) — standart qiymatlar
            Plan.objects.get_or_create(code=code, defaults=fields)
        if list:
            for p in Plan.objects.all():
                self.stdout.write(f"{p.code:20} {p.name} — muddat {p.duration_days or 'cheksiz'} kun, "
                                  f"{p.max_pages_per_case} varaq")
            return
        if not phone or not plan:
            raise CommandError("telefon va tarif kodi kerak")
        User = get_user_model()
        try:
            user = User.objects.get(phone_number=normalize_phone(phone))
            chosen = Plan.objects.get(code=plan)
        except (User.DoesNotExist, Plan.DoesNotExist) as e:
            raise CommandError(str(e))
        sub = quota.activate_subscription(user, chosen, days=days)
        self.stdout.write(f"{user} → {chosen.code}, tugaydi: {sub.expires_at or 'muddatsiz'}")
