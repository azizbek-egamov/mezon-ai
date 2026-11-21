"""Ish tahlili hisobotini rasmiy fayl (DOCX / PDF) sifatida eksport qilish va undan oldingi tasdiq (TZ §12).

1. `confirmation_info(report)` — "Yuridik tasdiqlash oynasi" uchun: xulosada keltirilgan barcha qonun manbalari
   (hujjat holati, tahrir), tekshiruvdan o'tmagan baholar ro'yxati.
2. Advokat tasdiqlagach (`CaseRun.lawyer_confirmed_at`), `build_blocks` hisobotni formatdan mustaqil bloklarga
   aylantiradi; `apps/doc_builder/writers.py` dagi `to_docx` / `to_pdf` ularni chizadi — mazmun bir xil.
Fayllar diskka yozilmaydi (xotirada yaratilib, darhol yuboriladi) — ochiq nusxa qolmasin.
"""
import re
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

from django.utils import timezone

from apps.doc_builder.writers import Block, to_docx, to_pdf  # noqa: F401 — views export.to_docx/to_pdf ni chaqiradi
from apps.lex_corpus.models import LegalActDocument

VERDICTS = {"qonun_buzilishi": "Qonun buzilishi", "buzilish_ehtimoli": "Buzilish ehtimoli",
            "huquqiy_ahamiyatli": "Huquqiy ahamiyatli", "asossiz": "Asossiz"}
IMPORTANCE = {"high": "yuqori", "medium": "oʻrta", "low": "past"}
DISCLAIMER = ("Ushbu hujjat MEZON AI tizimi tomonidan avtomatik tayyorlangan yordamchi materialdir va yuridik "
              "maslahat hisoblanmaydi. Yakuniy huquqiy pozitsiyani advokat belgilaydi.")
CITE_RE = re.compile(r"\[(M\d+)\]")


def _cited(legal: dict) -> set[str]:
    return set(CITE_RE.findall(f"{legal.get('assessment', '')}\n{legal.get('corrections', '')}"))


def _edition_of(lex_url: str) -> str:
    ondate = parse_qs(urlparse(lex_url).query).get("ONDATE")
    return f"{unquote(ondate[0])} tahriri" if ondate else "joriy tahrir"


def _doc_id(lex_url: str) -> int | None:
    m = re.search(r"/docs/(-?\d+)", lex_url)
    return abs(int(m.group(1))) if m else None


def confirmation_info(report: dict) -> dict:
    """Tasdiq oynasi: barcha keltirilgan moddalar (holati bilan) va tasdiqlanmagan baholar."""
    articles: dict[str, dict] = {}
    unverified = []
    for f in report.get("findings", []):
        legal = f.get("legal") or {}
        if legal.get("skipped"):
            continue
        if legal.get("error") or not (legal.get("verification") or {}).get("ok", False):
            issues = [i["detail"] for i in (legal.get("verification") or {}).get("issues", [])
                      if i.get("severity") == "error"]
            unverified.append({"topic": f["topic"], "reason": legal.get("error") or "; ".join(issues)[:400]
                               or "tekshiruvdan oʻtmagan"})
        cited = _cited(legal)
        for s in legal.get("sources", []):
            if s["key"] in cited and s["lex_url"] not in articles:
                articles[s["lex_url"]] = {"doc_title": s["doc_title"], "label": s["label"], "lex_url": s["lex_url"],
                                          "edition": _edition_of(s["lex_url"]), "doc_id": _doc_id(s["lex_url"])}
    statuses = dict(LegalActDocument.objects.filter(abs_id__in={a["doc_id"] for a in articles.values()})
                    .values_list("abs_id", "status"))
    status_names = {"ACTIVE": "kuchda", "REPEALED": "kuchini yoʻqotgan", "NOT_IN_FORCE": "kuchga kirmagan"}
    for a in articles.values():
        code = statuses.get(a.pop("doc_id"))
        a["status"] = status_names.get(code, "nomaʼlum")
        a["in_force"] = code == "ACTIVE"
    return {"articles": sorted(articles.values(), key=lambda a: (a["doc_title"], a["label"])),
            "unverified": unverified}


# ---------------------------------------------------------------------------- bloklar

def _plain_cites(text: str, sources: list[dict]) -> str:
    """[M3] -> [JPK 226-modda]: rasmiy hujjatda ichki kalit emas, modda nomi turadi."""
    by_key = {s["key"]: s for s in sources}

    def repl(m):
        s = by_key.get(m.group(1))
        return f"[{s['label'].split('.')[0]}]" if s else m.group(0)
    return CITE_RE.sub(repl, text or "")


def build_blocks(report: dict, title: str, lawyer_name: str, confirmed_at: datetime) -> list[Block]:
    local = timezone.localtime(confirmed_at)
    info = confirmation_info(report)
    b = [Block("title", "Ish hujjatlari tahlili"), Block("meta", title),
         Block("meta", f"Advokat tanishib chiqdi va tasdiqladi: {lawyer_name}, {local:%d.%m.%Y %H:%M}"),
         Block("warn", DISCLAIMER), Block("h1", "Xulosa"), Block("p", report.get("summary", ""))]
    facts = report.get("facts", [])
    findings = report.get("findings", [])
    b.append(Block("meta", f"{report.get('pages', 0)} varaq · {len(facts)} fakt "
                           f"({sum(1 for f in facts if f.get('verified'))} tasi varaqdagi iqtibos bilan tasdiqlangan) · "
                           f"{len(findings)} topilma"))
    if info["unverified"]:
        b.append(Block("h2", "Tasdiqlanmagan huquqiy baholar"))
        b.extend(Block("warn", f"{u['topic']}: {u['reason']}") for u in info["unverified"])

    for kind, heading in (("procedural", "Protsessual muammolar"), ("contradiction", "Ichki ziddiyatlar")):
        items = [f for f in findings if f["kind"] == kind]
        if not items:
            continue
        b.append(Block("h1", heading))
        for n, f in enumerate(items, 1):
            pages = ", ".join(f"{p}-varaq" for p in f.get("pages", []))
            b.append(Block("h2", f"{n}. {f['topic']}"))
            b.append(Block("meta", f"Muhimlik: {IMPORTANCE.get(f['importance'], f['importance'])} · Manba: {pages}"))
            b.append(Block("p", f["explanation"]))
            legal = f.get("legal") or {}
            if legal.get("skipped") or not legal.get("verdict"):
                continue
            ok = (legal.get("verification") or {}).get("ok", False)
            status = "manbalar tekshirildi" if ok else "TASDIQLANMAGAN — advokat alohida tekshirishi shart"
            b.append(Block("meta", f"Huquqiy baho: {VERDICTS.get(legal['verdict'], legal['verdict'])} · {status}"))
            sources = legal.get("sources", [])
            b.append(Block("p" if ok else "warn", _plain_cites(legal.get("assessment", ""), sources)))
            if legal.get("correction_needed") and legal.get("corrections"):
                b.append(Block("p", "Tuzatish: " + _plain_cites(legal["corrections"], sources)))
            if legal.get("defense_action"):
                b.append(Block("p", "Himoyachi uchun: " + legal["defense_action"]))
            cited = _cited(legal)
            for s in sources:
                if s["key"] in cited:
                    b.append(Block("bullet", f"{s['doc_title']} — {s['label']} ({_edition_of(s['lex_url'])}): {s['lex_url']}"))

    timeline = [next((f for f in facts if f["id"] == fid), None) for fid in report.get("timeline", [])]
    timeline = [f for f in timeline if f]
    if timeline:
        b.append(Block("h1", "Xronologiya"))
        b.extend(Block("bullet", f"{f.get('date', '')} {f.get('time', '')} · {f.get('verified_page') or f.get('page')}-varaq · "
                                 f"{f.get('summary', '')}") for f in timeline)

    b.append(Block("h1", "Foydalanilgan qonun hujjatlari"))
    for a in info["articles"]:
        b.append(Block("bullet", f"{a['doc_title']} — {a['label']} ({a['edition']}, hujjat {a['status']}): {a['lex_url']}"))
    if not info["articles"]:
        b.append(Block("p", "Qonun moddalari keltirilmagan."))
    b.append(Block("warn", DISCLAIMER))
    return b
