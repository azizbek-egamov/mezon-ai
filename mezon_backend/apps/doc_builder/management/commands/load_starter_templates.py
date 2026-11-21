"""Boshlang'ich shablonlarni (apps/doc_builder/starter_templates.py) bazaga yuklaydi yoki yangilaydi.

    python manage.py load_starter_templates

Sarlavha bo'yicha topadi; matn o'zgargan bo'lsa versiya oshadi va moderator tasdig'i bekor bo'ladi.
"""
from django.core.management.base import BaseCommand

from apps.doc_builder.models import DocumentTemplate
from apps.doc_builder.starter_templates import TEMPLATES


class Command(BaseCommand):
    help = "Boshlang'ich hujjat shablonlarini yuklaydi"

    def handle(self, *args, **opts):
        for spec in TEMPLATES:
            tpl = DocumentTemplate.objects.filter(title=spec["title"]).first() or DocumentTemplate(title=spec["title"])
            for key, value in spec.items():
                setattr(tpl, key, value)
            tpl.is_published = True  # moderator tasdiqlamaguncha "namuna" belgisi bilan ko'rinadi
            tpl.full_clean()
            tpl.save()
            self.stdout.write(f"  {tpl.title} — v{tpl.version}{' (tasdiqlangan)' if tpl.approved_at else ''}")
        self.stdout.write(f"Jami: {len(TEMPLATES)} ta shablon")
