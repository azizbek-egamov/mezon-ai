"""Ish hujjatini (PDF) tahlil qilish: sahifa matni -> PII niqoblash -> faktlar (varaq + iqtibos) -> tekshiruv ->
xronologiya -> ziddiyatlar va protsessual muammolar -> lex.uz moddalari bilan huquqiy asoslash.

    python manage.py analyze_case fixtures/cases/case_01/case_01.pdf --key fixtures/cases/case_01/answer_key.json
    python manage.py analyze_case --from-report data/case_runs/<vaqt>.json --key ...   # faqat huquqiy bosqich
"""
import json
import time
from collections import Counter
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.cases.analysis import Finding, find_issues, timeline
from apps.cases.case_types import CASE_TYPES
from apps.cases.extract import Fact, extract_facts
from apps.cases.legal import ground_findings
from apps.cases.pdf_text import Page, read_pdf_pages
from apps.cases.pii import PiiVault
from apps.rag.llm import get_llm
from apps.rag.store import get_client


def match_key(findings, key: dict) -> list[dict]:
    """Kalitdagi har bir band uchun varaqlari eng ko'p mos tushgan topilma. Moslik: umumiy varaqlar soni
    >= min(2, kalit varaqlari soni). Bu taxminiy mezon — natija jadvali qo'lda ham ko'rib chiqiladi."""
    rows = []
    for item in key["contradictions"] + key["procedural_issues"]:
        need = min(2, len(item["pages"]))
        best, best_overlap = None, 0
        for f in findings:
            overlap = len(set(f.pages) & set(item["pages"]))
            if overlap > best_overlap:
                best, best_overlap = f, overlap
        rows.append({"id": item["id"], "topic": item["topic"], "key_pages": item["pages"],
                     "found": best_overlap >= need, "finding": best.topic if best else None,
                     "finding_pages": best.pages if best else []})
    return rows


class Command(BaseCommand):
    help = "Ish hujjatini tahlil qiladi (faktlar, xronologiya, ziddiyatlar, huquqiy asoslash)"

    def add_arguments(self, parser):
        parser.add_argument("pdf", nargs="?")
        parser.add_argument("--from-report", help="Faktlar va topilmalarni oldingi hisobotdan olish (qayta to'lovsiz)")
        parser.add_argument("--key", help="answer_key.json — natijani solishtirish uchun")
        parser.add_argument("--extract-model", help="Faktlarni ajratish modeli (sukut: LLM_MODEL)")
        parser.add_argument("--effort", default="medium", choices=["low", "medium", "high"], help="Ziddiyatlar tahlili")
        parser.add_argument("--no-legal", action="store_true", help="Huquqiy asoslash bosqichisiz")
        parser.add_argument("--legal-effort", default="low", choices=["low", "medium", "high"])
        parser.add_argument("--legal-min-importance", default="medium", choices=["low", "medium", "high"],
                            help="Shundan past muhimlikdagi topilmalar huquqiy asoslanmaydi (xarajat tejash)")
        parser.add_argument("--legal-batch", type=int, default=4, help="Bitta LLM chaqiruvidagi topilmalar soni")
        parser.add_argument("--category", default="criminal", choices=sorted(CASE_TYPES), help="Ish turi (huquqiy qidiruv doirasi)")
        parser.add_argument("--budget", type=float, help="Shu buyruq uchun xarajat chegarasi, $ (LLM_BUDGET_USD o'rniga)")

    def handle(self, *args, pdf, from_report, key, extract_model, effort, no_legal, legal_effort,
               legal_min_importance, legal_batch, budget, category, **opts):
        llm = get_llm()
        if budget is not None and hasattr(llm, "budget_usd"):
            llm.budget_usd = budget
        t0 = time.monotonic()
        report: dict = {"created": datetime.now().isoformat(timespec="seconds")}
        vault = PiiVault()

        if from_report:
            with open(from_report, encoding="utf-8") as fh:
                prev = json.load(fh)
            facts = [Fact(**d) for d in prev["facts"]]
            findings = [Finding(**{k: v for k, v in d.items() if k != "legal"}) for d in prev["findings"]]
            summary = prev.get("summary", "")
            report.update({k: prev.get(k) for k in ("pdf", "pages", "pii_counts", "errors")})
            report["from_report"] = str(from_report)
            self.stdout.write(f"Oldingi hisobot: {len(facts)} fakt, {len(findings)} topilma")
            if not findings:  # faqat faktlar saqlangan (oraliq hisobot) — tahlil bosqichidan davom
                findings, summary = self._find_issues(facts, effort)
        elif pdf:
            facts, findings, summary = self._analyze(pdf, vault, extract_model, effort, report)
        else:
            raise CommandError("pdf yoki --from-report kerak")
        cost_before_legal = llm.cost_usd() if hasattr(llm, "cost_usd") else 0.0

        legal = []
        if not no_legal:
            t3 = time.monotonic()
            legal = ground_findings(findings, facts, effort=legal_effort, batch_size=legal_batch,
                                    min_importance=legal_min_importance, category=category)
            get_client().close()
            cost_legal = (llm.cost_usd() if hasattr(llm, "cost_usd") else 0.0) - cost_before_legal
            self._print_legal(findings, legal, time.monotonic() - t3, cost_legal)

        report.update({
            "facts": [f.to_dict() for f in facts], "summary": summary,
            "findings": [{**f.__dict__, "legal": (legal[i].__dict__ if legal else None)} for i, f in enumerate(findings)],
            "timeline": [f.id for f in timeline(facts)],
        })
        if key:
            self._evaluate(findings, key, report)
        cost_total = llm.cost_usd() if hasattr(llm, "cost_usd") else 0.0
        report.update({"cost_usd": round(cost_total, 4), "seconds": round(time.monotonic() - t0, 1)})
        out = self._write(report)
        self.stdout.write(f"\nJami: {report['seconds']} s, ${cost_total:.3f} | hisobot: {out}")

    # ------------------------------------------------------------------ bosqichlar

    def _analyze(self, pdf, vault, extract_model, effort, report):
        llm = get_llm()
        pages = read_pdf_pages(pdf)
        vault.learn_names([p.text for p in pages])  # shaxslar butun ish bo'yicha yig'iladi, keyin niqoblanadi
        masked = [Page(p.number, vault.mask(p.text)) for p in pages]
        empty = [p.number for p in pages if p.is_empty]
        self.stdout.write(f"Sahifalar: {len(pages)} (matnsiz: {empty or 'yoʻq'}) | niqoblangan PII: "
                          f"{sum(vault.counters.values())} ta {dict(vault.counters)}")
        t1 = time.monotonic()
        facts, errors = extract_facts(masked, model=extract_model)
        verified = [f for f in facts if f.verified]
        self.stdout.write(f"Faktlar: {len(facts)} | iqtibosi tasdiqlangan: {len(verified)} "
                          f"({len(verified) / max(1, len(facts)):.0%}) | {time.monotonic() - t1:.0f} s | ${llm.cost_usd():.3f}")
        for e in errors:
            self.stdout.write(f"  ✗ {e}")
        # Sahifa matnlari hisobotga yozilmaydi; niqoblangan matn faqat PII sizmaganini tekshirish uchun saqlanadi.
        report.update({"pdf": str(pdf), "pages": len(pages), "pii_counts": vault.counters, "errors": errors})
        self._masked = masked
        # Oraliq saqlash: keyingi bosqich xato bersa ham faktlar yo'qolmasin (--from-report bilan davom etiladi).
        checkpoint = self._write({**report, "facts": [f.to_dict() for f in facts], "findings": []}, suffix="_facts")
        self.stdout.write(f"Faktlar saqlandi: {checkpoint}")
        findings, summary = self._find_issues(facts, effort)
        self.stdout.write(f"Xulosa: {vault.unmask(summary)}")
        return facts, findings, summary

    def _find_issues(self, facts, effort):
        t2 = time.monotonic()
        findings, summary = find_issues(facts, effort=effort)
        self.stdout.write(f"Tahlil: {len(findings)} topilma | {time.monotonic() - t2:.0f} s")
        return findings, summary

    def _write(self, report: dict, suffix: str = "") -> str:
        out_dir = settings.DATA_DIR / "case_runs"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{datetime.now():%Y%m%d_%H%M%S}{suffix}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out)

    def _print_legal(self, findings, legal, seconds, cost):
        done = [a for a in legal if not a.skipped]
        verdicts = Counter(a.verdict or "xato" for a in done)
        ok = sum(1 for a in done if a.verification.get("ok"))
        quotes = sum(a.verification.get("quotes_checked", 0) for a in done)
        corrected = [a for a in done if a.correction_needed]
        self.stdout.write(f"\nHUQUQIY ASOSLASH: {len(done)} topilma (oʻtkazib yuborildi: {len(legal) - len(done)}) | "
                          f"{seconds:.0f} s | ${cost:.3f}")
        self.stdout.write(f"  Xulosalar: {dict(verdicts)} | tekshiruvdan oʻtdi: {ok}/{len(done)} | "
                          f"tekshirilgan iqtiboslar: {quotes} | tuzatish kiritilgan: {len(corrected)} | "
                          f"qayta baholangan: {sum(a.retried for a in done)}")
        for f, a in zip(findings, legal):
            if a.skipped:
                continue
            mark = "✓" if a.verification.get("ok") else "⚠"
            arts = "; ".join(f"{s['key']} {s['label'][:38]}" for s in a.sources if s["key"] in a.verification.get("citations", []))
            self.stdout.write(f"\n  {mark} [{a.verdict or a.error[:40]}] {f.topic} ({a.model}{', qayta' if a.retried else ''})")
            self.stdout.write(f"     Manbalar: {arts or '-'}")
            self.stdout.write(f"     {a.assessment[:420]}")
            if a.correction_needed:
                self.stdout.write(f"     Tuzatish: {a.corrections[:300]}")
            for issue in a.verification.get("issues", []):
                self.stdout.write(f"     {'✗' if issue['severity'] == 'error' else '!'} {issue['detail'][:160]}")

    def _evaluate(self, findings, key_path, report):
        with open(key_path, encoding="utf-8") as fh:
            answer_key = json.load(fh)
        rows = match_key(findings, answer_key)
        found = sum(r["found"] for r in rows)
        self.stdout.write(f"\nJAVOBLAR KALITI BILAN SOLISHTIRISH: {found}/{len(rows)} topildi")
        for r in rows:
            self.stdout.write(f"  {'✓' if r['found'] else '✗'} {r['id']} {r['topic'][:45]:<45} kalit {r['key_pages']} "
                              f"-> {(r['finding'] or '-')[:45]} {r['finding_pages']}")
        evaluation = {"found": found, "total": len(rows), "rows": rows}
        masked = getattr(self, "_masked", None)
        if masked is not None:
            leaked = [v for v in answer_key.get("pii_values", []) + answer_key.get("pii_names", [])
                      if any(v in p.text for p in masked)]
            self.stdout.write(f"PII: LLM ga yuborilgan matnda ochiq qolgan qiymatlar: {leaked or 'yoʻq'}")
            evaluation["pii_leaked"] = leaked
        report["evaluation"] = evaluation
