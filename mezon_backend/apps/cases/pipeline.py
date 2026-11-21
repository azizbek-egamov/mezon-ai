"""Ish tahlili zanjiri (veb va buyruq uchun umumiy): PDF -> PII niqoblash -> faktlar -> ziddiyatlar -> huquqiy
asoslash -> ko'rsatishga tayyor hisobot (niqobdan chiqarilgan, chunki asl PDF ham serverda saqlanadi).

progress(foiz, bosqich_nomi) har bir bosqichda chaqiriladi.
"""
import time

from django.conf import settings

from apps.rag.llm import get_llm

from .analysis import find_issues, timeline
from .extract import extract_facts
from .legal import ground_findings
from .pdf_text import Page, read_pdf_pages
from .pii import PiiVault


def _noop(pct: int, stage: str) -> None:
    pass


def analyze_pdf(pdf_path: str, progress=_noop, category: str = "criminal",
                legal_min_importance: str = "medium") -> dict:
    llm = get_llm()
    cost0 = llm.cost_usd() if hasattr(llm, "cost_usd") else 0.0
    t0 = time.monotonic()

    progress(2, "PDF oʻqilmoqda")
    pages = read_pdf_pages(pdf_path, on_progress=lambda done, total: progress(
        2 + int(6 * done / total), f"Skaner sahifalar OCR: {done}/{total}"))
    if hasattr(llm, "extend_budget"):  # katta ish (ko'p varaq) — kattaroq chegara
        llm.extend_budget(max(settings.CASE_BUDGET_USD, settings.CASE_BUDGET_PER_PAGE_USD * len(pages)))
    vault = PiiVault()
    vault.learn_names([p.text for p in pages])
    masked = [Page(p.number, vault.mask(p.text)) for p in pages]
    progress(8, f"{len(pages)} varaq, shaxsiy maʼlumotlar niqoblandi")

    facts, errors = extract_facts(
        masked, on_progress=lambda done, total: progress(8 + int(42 * done / total), f"Faktlar: {done}/{total} blok"),
        case_type=category)
    progress(52, f"{len(facts)} ta fakt ajratildi; ziddiyatlar tahlil qilinmoqda")

    findings, summary = find_issues(facts, case_type=category)
    progress(70, f"{len(findings)} ta topilma; lex.uz moddalari bilan asoslanmoqda")

    legal = ground_findings(findings, facts, min_importance=legal_min_importance, category=category)
    progress(98, "Hisobot tayyorlanmoqda")

    u = vault.unmask
    tl = timeline(facts)
    report = {
        "case_type": category, "pages": len(pages), "empty_pages": [p.number for p in pages if p.is_empty],
        "ocr_pages": [{
            "page": p.number, "source": p.source, "confidence": p.ocr_confidence, "low_quality": p.low_quality,
            "has_handwriting": p.has_handwriting, "stamps": p.stamps, "cost_usd": p.ocr_cost_usd,
            "warning": p.ocr_warning
        } for p in pages if p.source != "text"],
        "ocr_cost_usd": round(sum(p.ocr_cost_usd for p in pages), 4),
        "manifest": [{"page": p.number, "source": p.source, "has_handwriting": p.has_handwriting,
                      "stamps": p.stamps, "chars": len(p.text)} for p in pages],
        "pii_counts": vault.counters, "errors": errors, "summary": u(summary),
        "facts": [{**f.to_dict(), "summary": u(f.summary), "quote": u(f.quote), "source": u(f.source)} for f in facts],
        "findings": [],
        "timeline": [f.id for f in tl],
        "cost_usd": round((llm.cost_usd() if hasattr(llm, "cost_usd") else 0.0) - cost0, 4),
        "seconds": round(time.monotonic() - t0, 1),
    }
    for f, a in zip(findings, legal):
        report["findings"].append({
            "kind": f.kind, "topic": u(f.topic), "importance": f.importance, "pages": f.pages,
            "fact_ids": f.fact_ids, "explanation": u(f.explanation),
            "legal": {**a.__dict__, "assessment": u(a.assessment), "corrections": u(a.corrections),
                      "defense_action": u(a.defense_action)},
        })
    return report
