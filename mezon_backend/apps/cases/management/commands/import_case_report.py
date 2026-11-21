"""analyze_case hisobotini (data/case_runs/*.json) veb sahifada ko'rsatish uchun import qilish — API to'lovisiz.

    python manage.py import_case_report data/case_runs/20261025_144120.json --pdf fixtures/cases/case_01/case_01.pdf --owner +998901234567
"""
import json
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import normalize_phone
from apps.cases import storage
from apps.cases.models import CaseRun


class Command(BaseCommand):
    help = "Tayyor tahlil hisobotini CaseRun sifatida import qiladi"

    def add_arguments(self, parser):
        parser.add_argument("report")
        parser.add_argument("--pdf", required=True)
        parser.add_argument("--title", default="")
        parser.add_argument("--owner", required=True, help="Ish egasining telefon raqami")

    def handle(self, *args, report, pdf, title, owner, **opts):
        user = get_user_model().objects.get(phone_number=normalize_phone(owner))
        data = json.loads(storage.read_file(report))
        run_id = uuid.uuid4()
        out = settings.DATA_DIR / "case_runs" / f"web_{run_id}.json"
        data.setdefault("timeline", [])
        data.setdefault("pii_counts", {})
        out = storage.write_encrypted(out, json.dumps(data, ensure_ascii=False).encode("utf-8"))
        run = CaseRun.objects.create(
            id=run_id, owner=user, title=title or f"Import: {report}", pdf_path=str(pdf), pages=data.get("pages") or 0,
            status=CaseRun.Status.DONE, progress=100, stage="Tayyor (import)", report_path=str(out),
            cost_usd=data.get("cost_usd") or 0)
        self.stdout.write(f"/cases/{run.id}/")
