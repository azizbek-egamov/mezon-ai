"""lex.uz reyestr JSON ini (barcha_57950_hujjat.json) legal_act_document ga import qilish.

    python manage.py import_registry [--path FILE]
"""
import json
from collections import Counter
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.lex_corpus import normalize as N
from apps.lex_corpus.models import LegalActDocument

UPDATE_FIELDS = [
    "lex_id_lat", "lex_id_cyr", "doc_type", "act_type_raw", "hierarchy_weight", "official_number",
    "adoption_date", "title_uz_lat", "title_uz_cyr", "title_ru", "title_search", "status",
    "is_amending", "corpus_tier",
]


def parse_date(s: str):
    try:
        return datetime.strptime(s, "%d.%m.%Y").date() if s else None
    except ValueError:
        return None


def build_documents(rows: list[dict]) -> dict[int, LegalActDocument]:
    """Bir abs_id dagi lotin/kirill nusxalarni bitta hujjatga birlashtiradi."""
    docs: dict[int, LegalActDocument] = {}
    for r in rows:
        lex_id = r["id"]
        abs_id = abs(int(lex_id))
        title = N.normalize_title(r["title"])
        script = N.detect_script(title)
        doc = docs.get(abs_id)
        if doc is None:
            doc = docs[abs_id] = LegalActDocument(abs_id=abs_id, act_type_raw=r["act_type"].strip(),
                                                  official_number=r["act_number"].strip(),
                                                  adoption_date=parse_date(r["act_date"]),
                                                  status=N.map_status(r["status"]))
        if script == "lat":
            doc.lex_id_lat = doc.lex_id_lat or lex_id
            doc.title_uz_lat = doc.title_uz_lat or title
        elif N.is_russian(title):
            doc.lex_id_cyr = doc.lex_id_cyr or lex_id
            doc.title_ru = doc.title_ru or title
        else:
            doc.lex_id_cyr = doc.lex_id_cyr or lex_id
            doc.title_uz_cyr = doc.title_uz_cyr or title
    for doc in docs.values():
        any_title = doc.title_uz_lat or doc.title_uz_cyr or doc.title_ru
        doc.doc_type = N.classify_doc_type(doc.abs_id, doc.act_type_raw, any_title, doc.official_number)
        doc.hierarchy_weight = N.HIERARCHY_WEIGHT[doc.doc_type]
        doc.is_amending = N.is_amending(any_title)
        doc.corpus_tier = N.corpus_tier(doc.doc_type, doc.status)
        doc.title_search = any_title.lower()
    return docs


class Command(BaseCommand):
    help = "lex.uz reyestr JSON faylini bazaga import qiladi (qayta ishga tushirish xavfsiz)."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=str(settings.LEX_REGISTRY_JSON))

    def handle(self, *args, path, **opts):
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        docs = build_documents(rows)
        with transaction.atomic():
            LegalActDocument.objects.bulk_create(
                docs.values(), batch_size=2000, update_conflicts=True,
                unique_fields=["abs_id"], update_fields=UPDATE_FIELDS,
            )
        self.stdout.write(f"Yozuvlar: {len(rows)} -> hujjatlar: {len(docs)}")
        for name, key in [("Tur", "doc_type"), ("Qatlam", "corpus_tier"), ("Status", "status")]:
            c = Counter(getattr(d, key) for d in docs.values())
            self.stdout.write(f"{name}: " + ", ".join(f"{k}={v}" for k, v in c.most_common()))
        core = [d for d in docs.values() if d.corpus_tier == "CORE"]
        self.stdout.write(f"Yadro: {len(core)} (o'zgartirish kirituvchi emas: "
                          f"{sum(not d.is_amending for d in core)})")
