"""Akkauntlar paydo bo'lishidan oldin yuklangan (egasiz) ishlarni foydalanuvchiga biriktiradi.

    python manage.py assign_cases +998901234567
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import normalize_phone
from apps.cases.models import CaseRun


class Command(BaseCommand):
    help = "Egasiz ishlarni telefon raqami bo'yicha foydalanuvchiga biriktiradi"

    def add_arguments(self, parser):
        parser.add_argument("phone")

    def handle(self, *args, phone, **opts):
        try:
            user = get_user_model().objects.get(phone_number=normalize_phone(phone))
        except get_user_model().DoesNotExist:
            raise CommandError("Bunday foydalanuvchi yoʻq")
        n = CaseRun.objects.filter(owner=None).update(owner=user)
        self.stdout.write(f"{n} ta ish {user} ga biriktirildi")
