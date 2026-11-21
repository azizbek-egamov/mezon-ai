"""Deterministik huquqiy tekshiruvchi (TZ §4.3: 1 — iqtibos bazada va sanada kuchda; 2 — istisnolar tushmagan).

`answer.verify_answer` dan keyin ishlaydi va bazaga murojaat qiladi (u esa faqat manba matnlari bilan ishlaydi):

1. Keltirilgan manbalar ([M#]):
   - hujjat kuchdami (status ACTIVE) — kuchini yo'qotgan hujjatga tayanish — xato;
   - voqea sanasi berilgan bo'lsa, sanadagi tahrir aniqlanganmi (aniqlanmagan — ogohlantirish).
2. Matndagi "JK 168-modda", "Jinoyat-protsessual kodeksining 226-moddasi 2-qismi" kabi havolalar bazadan qidiriladi:
   - hujjatda bunday modda yo'q — xato (modda o'ylab topilgan);
   - voqea sanasida hali kuchga kirmagan yoki o'sha sanaga qadar chiqarib tashlangan — xato;
   - qism raqami moddadagi qismlar sonidan katta — ogohlantirish (qismlar abzatslardan taxminan sanaladi).
3. Istisnolar: «iqtibos» olingan qismda iqtibosga kirmagan "…bundan mustasno", "…qo'llanilmaydi" kabi gap bo'lsa va
   javobda u tilga olinmagan bo'lsa — ogohlantirish (istisno tushib qolgan bo'lishi mumkin). Moddada "Izoh" bo'lsa
   va javobda e'tiborga olinmagan bo'lsa — ma'lumot (info).
"""
import re
from datetime import date

from django.utils.translation import gettext as _

from apps.lex_corpus.history import as_of
from apps.lex_corpus.models import LegalActArticle, LegalActDocument, Status
from apps.lex_corpus.normalize import normalize_apostrophes

from .answer import QUOTE_RE, Issue, Source, _norm
from .search import CODE_ALIASES

ARTICLE_MENTION_RE = re.compile(r"(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)\s*-\s*modda\w*"
                                r"(?:\s+(\d+|[a-zʻ']+)\s*-?\s*qism)?", re.I)
ORDINALS = {"birinchi": 1, "ikkinchi": 2, "uchinchi": 3, "toʻrtinchi": 4, "beshinchi": 5, "oltinchi": 6,
            "yettinchi": 7, "sakkizinchi": 8, "toʻqqizinchi": 9, "oʻninchi": 10}
EXCEPTION_RE = re.compile(r"mustasno|qoʻllanilmaydi|qoʻllanmaydi|tatbiq etilmaydi|taalluqli emas|"
                          r"за исключением|не применя|не распростран", re.I)
BAND_LINE_RE = re.compile(r"^\s*(?:[a-zа-я]\)|[a-zа-я]\s*[\-–—]|\d+\))", re.I)  # "a) ..." — band, qism emas
ALIAS_WINDOW = 90


def _part_lines(article: LegalActArticle, lang: str | None = None) -> list[str]:
    """Moddaning qismlari (taxminan): lex.uz da qism — abzats. Yangi qism bosh harf bilan boshlanadi va oldingi
    abzats nuqta bilan tugaydi; "a) ..." bandlari va ulardan keyingi "…jazolanadi" sanksiya qatori — o'sha qism
    davomi. Har bir qism uning barcha abzatslari bilan bitta satr bo'lib qaytadi."""
    text = article.text_in(lang) if lang and article.has_lang(lang) else article.primary_text
    parts: list[str] = []
    for line in (raw.strip() for raw in text.split("\n")):
        if not line:
            continue
        starts_part = (not parts or (line[0].isupper() and not BAND_LINE_RE.match(line)
                                     and parts[-1].rstrip().endswith((".", ":"))))
        if starts_part and parts and parts[-1].rstrip().endswith(":"):
            starts_part = False  # "Firibgarlik:" dan keyingi qatorlar — sanab o'tish
        if starts_part:
            parts.append(line)
        else:
            parts[-1] += "\n" + line
    return parts


def _exception_clause(sentence_n: str) -> str:
    """Istisno bo'lagi: belgidan oldingi ~60 belgi ("…odam o'lishiga sabab bo'lgan hollar") va undan keyingi qism —
    javobda shu bo'lak bayon qilingan-qilinmaganini solishtirish uchun (so'zlar bo'yicha)."""
    start = max(0, EXCEPTION_RE.search(sentence_n).start() - 60)
    return re.sub(r"\W+", " ", sentence_n[start:]).strip()


def _resolve_doc_ids(answer: str, pos: int, sources: list[Source]) -> list[int]:
    """Havola oldidagi qisqa oynadan kodeks nomini topadi ("JPK 226-modda", "Jinoyat kodeksining 168-moddasi")."""
    window = answer[max(0, pos - ALIAS_WINDOW):pos]
    window = re.split(r"[.;!?\n]", window)[-1].lower()
    best, best_end = None, -1
    for pattern, ids in CODE_ALIASES.items():
        for m in re.finditer(pattern, window):
            if m.end() > best_end:
                best, best_end = ids, m.end()
    return best or []


def _article_of(source: Source) -> LegalActArticle | None:
    """Manbaning to'liq moddasi: voqea sanasidagi versiya yoki joriy modda."""
    version_id = (source.hit.as_of or {}).get("version_id")
    pk = version_id or source.hit.article_id
    return LegalActArticle.objects.select_related("document", "edition").filter(pk=pk).first()


def check_sources(answer: str, sources: list[Source], on_date: date | None) -> list[Issue]:
    issues = []
    cited = set(re.findall(r"\[(M\d+)\]", answer))
    for s in sources:
        if s.key not in cited:
            continue
        doc = (LegalActDocument.objects.filter(abs_id=s.hit.document_id)
               .only("status", "title_uz_lat", "history_from").first())
        if doc is not None and doc.status != Status.ACTIVE:
            issues.append(Issue("error", "hujjat_kuchda_emas",
                                _("[%(key)s] %(title)s — hujjat kuchda emas (%(status)s)") % {"key": s.key, "title": s.hit.doc_title, "status": doc.get_status_display()}))
        if on_date and (s.hit.as_of or {}).get("state") == "unknown":
            # Tarixi umuman yuklanmagan hujjat (masalan, Plenum qarorlari — kam o'zgaradi) — ma'lumot;
            # tarix bor, lekin sana undan oldin — ogohlantirish (eski tahrir tekshirilmadi).
            severity = "info" if doc is not None and doc.history_from is None else "warning"
            issues.append(Issue(severity, "tahrir_nomalum",
                                _("[%(key)s] %(label)s: %(note)s") % {"key": s.key, "label": s.hit.label, "note": s.hit.as_of.get('note') or _('sanadagi tahrir aniqlanmadi')}))
    return issues


def check_mentions(answer: str, sources: list[Source], on_date: date | None) -> list[Issue]:
    issues = []
    source_docs = sorted({s.hit.document_id for s in sources})
    seen = set()
    for m in ARTICLE_MENTION_RE.finditer(answer):
        number, part_raw = m.group(1), (m.group(2) or "").lower()
        doc_ids = _resolve_doc_ids(answer, m.start(), sources) or source_docs
        key = (tuple(doc_ids), number, part_raw)
        if key in seen:
            continue
        seen.add(key)
        rows = list(LegalActArticle.objects.select_related("document", "edition")
                    .filter(document_id__in=doc_ids, article_number=number, unit_type="ARTICLE"))
        if not rows:
            named = _resolve_doc_ids(answer, m.start(), sources)
            if named and LegalActDocument.objects.filter(abs_id__in=named, last_synced_at__isnull=False).exists():
                title = LegalActDocument.objects.get(abs_id=named[0]).title_uz_lat
                issues.append(Issue("error", "modda_yoq", _("%(number)s-modda %(title)s da yoʻq — modda oʻylab topilgan") % {"number": number, "title": title}))
            continue
        current = [r for r in rows if r.edition.is_current]
        if on_date:
            valid = [r for r in rows if r.document.history_from and r.document.history_from <= on_date
                     and r.is_valid_on(on_date)]
            known = [r for r in rows if r.document.history_from and r.document.history_from <= on_date]
            if known and not valid:
                first = min((r.valid_from for r in rows if r.valid_from), default=None)
                if first and on_date < first:
                    detail = _("%(number)s-modda %(first)s dan kuchga kirgan — %(date)s da yoʻq edi") % {
                        "number": number, "first": f"{first:%d.%m.%Y}", "date": f"{on_date:%d.%m.%Y}"}
                else:
                    detail = _("%(number)s-modda %(date)s da kuchda boʻlmagan (chiqarib tashlangan)") % {
                        "number": number, "date": f"{on_date:%d.%m.%Y}"}
                issues.append(Issue("error", "modda_sanada_kuchda_emas", detail))
                continue
        elif not current:
            issues.append(Issue("error", "modda_kuchda_emas", _("%(number)s-modda hozirgi tahrirda yoʻq (chiqarilgan)") % {"number": number}))
            continue
        if part_raw:
            part = int(part_raw) if part_raw.isdigit() else ORDINALS.get(normalize_apostrophes(part_raw))
            article = (current or rows)[0]
            if part and part > len(_part_lines(article)):
                issues.append(Issue("warning", "qism_yoq",
                                    _("%(number)s-moddaning %(part)s-qismi topilmadi (moddada ~%(count)s qism)") % {
                                        "number": number, "part": part, "count": len(_part_lines(article))}))
    return issues


def check_exceptions(answer: str, sources: list[Source]) -> list[Issue]:
    issues = []
    by_key = {s.key: s for s in sources}
    answer_n = _norm(answer)
    noted = set()
    for m in QUOTE_RE.finditer(answer):
        quote = _norm(m.group(1) or m.group(2)).strip(" .,;:")
        cite = re.match(r"\s*[.,;:]?\s*\[(M\d+)\]", answer[m.end():])
        source = by_key.get(cite.group(1)) if cite else None
        article = _article_of(source) if source else None
        if article is None:
            continue
        pieces = [p.strip(" .,;:") for p in quote.split("...") if len(p.strip()) >= 8]
        answer_words = re.sub(r"\W+", " ", answer_n)
        for line in _part_lines(article, source.hit.payload.get("lang")):
            line_n = _norm(line)
            if not pieces or not all(p in line_n for p in pieces):
                continue
            if EXCEPTION_RE.search(quote):  # istisno iqtibosning o'zida keltirilgan
                break
            # Iqtibos olingan qism: undagi istisno gapi javobda (iqtibos yoki bayon sifatida) bormi?
            for sentence in re.split(r"(?<=[.;])\s+", line):
                sent_n = _norm(sentence)
                if not EXCEPTION_RE.search(sentence) or sent_n in noted:
                    continue
                clause = _exception_clause(sent_n)
                if clause and clause[:40] in answer_words:
                    continue
                noted.add(sent_n)
                issues.append(Issue("warning", "istisno_tushgan",
                                    _("[%(key)s] %(label)s: iqtibos olingan qismda istisno bor, javobda eʼtiborga olinmagan — «%(sentence)s»") % {
                                        "key": cite.group(1), "label": source.hit.label, "sentence": sentence.strip()[:200]}))
            break
        lang = source.hit.payload.get("lang")
        text = article.text_in(lang) if lang and article.has_lang(lang) else article.primary_text
        if re.search(r"^\s*(Izoh|Изоҳ|Примечание)\b", text, re.M) and not any(w in answer_n for w in ("izoh", "изоҳ", "примечани")) \
                and ("izoh", article.pk) not in noted:
            noted.add(("izoh", article.pk))
            issues.append(Issue("info", "izoh_bor", _("[%(key)s] %(label)s: moddada «Izoh» bor — atamalar taʼrifini tekshiring") % {
                "key": cite.group(1), "label": source.hit.label}))
    return issues


def verify_legal(answer: str, sources: list[Source], on_date: date | None = None) -> list[Issue]:
    """Bazaga tayanadigan tekshiruvlar; natija verify_answer issues ga qo'shiladi (error — tekshiruvdan o'tmagan)."""
    answer = normalize_apostrophes(answer)
    return check_sources(answer, sources, on_date) + check_mentions(answer, sources, on_date) + \
        check_exceptions(answer, sources)
