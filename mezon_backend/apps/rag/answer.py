"""Iqtibosli huquqiy javob: qidiruv natijalari -> manbalar [M1..Mn] -> LLM javobi (stream) -> kod tekshiruvi.

Model faqat berilgan manbalardan foydalanadi, har bir huquqiy fikrga [M#] qo'yadi, qonundan iqtibosni «...»
ichida aynan ko'chiradi. Javob tugagach `verify_answer` uni deterministik tekshiradi (TZ §4.3, 1-2 tekshiruv):
  - [M#] mavjud manbaga ishora qiladimi;
  - har bir «iqtibos» manba matnida so'zma-so'z bormi;
  - tilga olingan "N-modda" lar manbalarda bormi (bo'lmasa — modda o'ylab topilgan bo'lishi mumkin).
"""
import re
from dataclasses import dataclass, field

from django.utils.translation import gettext as _

from apps.lex_corpus.normalize import normalize_apostrophes

from .search import SearchHit


LANG_NAMES = {
    "uz-Latn": "oʻzbek tilida (lotin yozuvida)",
    "uz-Latn-2026": "oʻzbek tilida (2026-yilgi yangi lotin yozuvida: ğ, ö, ş, ç harflari bilan)",
    "uz-Cyrl": "oʻzbek tilida (kirill yozuvida)",
    "ru": "rus tilida",
    "kaa": "qoraqalpoq tilida",
    "en": "ingliz tilida",
}

SYSTEM = """Sen MEZON AI — Oʻzbekiston qonunchiligi boʻyicha advokatlarga yordam beruvchi yuridik yordamchisan.

Qoidalar:
1. FAQAT <manbalar> ichidagi matnlarga tayan. Manbalarda javob boʻlmasa, buni ochiq ayt va qaysi maʼlumot yetishmasligini yoz. Taxmin qilma.
2. Har bir huquqiy fikrdan keyin manbani kvadrat qavsda koʻrsat: [M1], [M2]. Bir fikr bir nechta manbaga tayansa: [M1][M3].
3. Qonundan iqtibos keltirsang, uni «...» ichida manbadagi matndan AYNAN koʻchir — soʻz, harf va tinish belgisini oʻzgartirma, qisqartirma, tarjima qilma — va iqtibosdan KEYIN DARHOL manbani qoʻy: «...» [M1].
4. Manbalarda yoʻq modda, band yoki hujjat raqamini tilga olma va oʻylab topma.
5. Javob tuzilishi: avval qisqa xulosa (2-4 gap, barcha yoʻnalishlar boʻyicha), keyin asoslash — manbalardagi har bir yoʻnalish (yonalish atributi) uchun alohida boʻlim (moddalar, qismlar, jazolar, muddatlar, tartib), oxirida eʼtibor berish kerak boʻlgan holatlar (istisnolar, ogʻirlashtiruvchi belgilar, yoʻnalishlar orasidagi bogʻliqlik). Javobga aloqasi yoʻq manbani ishlatma.
6. Javob oxirida javob tilida bir qator ogohlantirish: maʼlumot tanishish uchun, yakuniy huquqiy xulosani advokat beradi.
8. Manbada [Voqea sanasidagi tahrir] va [Hozirgi tahrir] berilgan boʻlsa, voqea sanasidagisini qoʻlla; keyingi oʻzgarish ahvolni yengillashtirsa (jazo yumshatilgan, qilmish jinoyat emas deb topilgan), buni alohida koʻrsat — bunday qonun orqaga qaytish kuchiga ega boʻlishi mumkin.
9. Agar foydalanuvchi qisqa salomlashsa, hol-ahvol soʻrasa yoki minnatdorchilik bildirsa (masalan: 'salom', 'rahmat'), qonun moddalarini tahlil qilma, choʻzib 1 dunyo gap yozma! Qisqa va samimiy (1-2 gapda) salomlashib, qanday huquqiy yordam kerakligini soʻra.
10. Har qanday savolga aniq, loʻnda va faqat zaruriy darajada ixcham javob ber. Ortiqcha soʻzbozlik qilma."""


@dataclass
class Source:
    key: str
    hit: SearchHit

    def render(self) -> str:
        h = self.hit
        edition = h.payload.get("edition", "")
        topic = f' yonalish="{h.topic}"' if h.topic else ""
        head = f'<manba id="{self.key}"{topic} hujjat="{h.doc_title}" qism="{h.label}" tahrir="{edition}" havola="{h.lex_url}"'
        if h.payload.get("translation_stale"):  # kirill/rus tarjimasi asosiy tahrirdan orqada (TZ §5.4)
            head += ' ogohlantirish="bu til versiyasining tahriri lotin matnidan farq qiladi — eskirgan boʻlishi mumkin"'
        if h.payload.get("lang_fallback"):
            head += ' ogohlantirish="rasmiy matn soʻralgan tilda yoʻq — asl tilda berilgan"'
        if not h.as_of:
            return f"{head}>\n{h.text}\n</manba>"
        # Voqea sanasi berilgan: matn — o'sha sanadagi tahrir; o'zgargan bo'lsa hozirgisi ham beriladi
        # (orqaga qaytish kuchini baholash uchun, JK 13-modda).
        head += f' voqea_sanasi="{h.as_of["date"]}"'
        if h.as_of["state"] != "changed":
            note = f"\n[Izoh: {h.as_of['note']}]" if h.as_of.get("note") else ""
            return f"{head}>\n{h.text}{note}\n</manba>"
        return (f"{head}>\n[Voqea sanasidagi tahrir — {h.as_of['note']}]\n{h.text}\n"
                f"[Hozirgi tahrir]\n{h.current_text}\n</manba>")


def build_sources(hits: list[SearchHit], max_sources: int | None = None) -> list[Source]:
    return [Source(key=f"M{i}", hit=h) for i, h in enumerate(hits[:max_sources] if max_sources else hits, 1)]


def build_prompt(question: str, sources: list[Source], lang: str = "uz-Latn") -> tuple[str, str]:
    system = f"{SYSTEM}\n7. Javobni {LANG_NAMES.get(lang, LANG_NAMES['uz-Latn'])} yoz; iqtiboslar esa manbadagi tilda qoladi."
    user = "<manbalar>\n" + "\n\n".join(s.render() for s in sources) + f"\n</manbalar>\n\nSavol: {question}"
    return system, user


# ---------- Tekshiruv ----------

CITE_RE = re.compile(r"\[(M\d+)\]")
# Qonun iqtibosi = «...» dan keyin darhol [M#] (promptdagi 3-qoida). Boshqa «...» lar (masalan rus tilidagi
# oddiy qo'shtirnoq) iqtibos hisoblanmaydi va tekshirilmaydi. Arzon modellar ba'zan «» o'rniga "..." / “...” yozadi —
# [M#] dan oldin kelsa, ular ham iqtibos sifatida xuddi shunday aynan tekshiriladi.
QUOTE_RE = re.compile(r"(?:«([^»]{3,})»|[\"“]([^\"”“]{3,})[\"”])\s*[.,;:]?\s*(?=((?:\[M\d+\][\s,;]*)+))")
ARTICLE_MENTION_RE = re.compile(r"(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)\s*-\s*modda")


@dataclass
class Issue:
    severity: str  # "error" | "warning"
    kind: str
    detail: str


@dataclass
class VerificationReport:
    citations: list[str] = field(default_factory=list)
    quotes_checked: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


def _norm(text: str) -> str:
    text = normalize_apostrophes(text).replace("…", "...").replace("\u200e", "")
    text = re.sub(r"[“”„\"]", '"', text)
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_answer(answer: str, sources: list[Source]) -> VerificationReport:
    by_key = {s.key: s for s in sources}
    report = VerificationReport()

    cited = list(dict.fromkeys(CITE_RE.findall(answer)))
    report.citations = cited
    for key in cited:
        if key not in by_key:
            report.issues.append(Issue("error", "manba_yoq", _("[%(key)s] — bunday manba berilmagan") % {"key": key}))
    if not cited:
        report.issues.append(Issue("error", "iqtibossiz", _("Javobda birorta ham [M#] manba havolasi yo'q")))

    # Iqtibos voqea sanasidagi yoki hozirgi tahrirdan bo'lishi mumkin (ikkalasi ham rasmiy matn).
    corpus = {s.key: _norm(f"{s.hit.text}\n{s.hit.current_text}") for s in sources}
    for m in QUOTE_RE.finditer(answer):
        quote = m.group(1) or m.group(2)
        report.quotes_checked += 1
        q = _norm(quote).strip(" .,;:")
        # "...": iqtibosning qismlari alohida tekshiriladi (model qisqartirgan bo'lsa ham har bir qism aynan bo'lsin)
        pieces = [p.strip(" .,;:") for p in q.split("...") if len(p.strip()) >= 8]
        in_any = bool(pieces) and all(any(p in text for text in corpus.values()) for p in pieces)
        if not in_any:
            report.issues.append(Issue("error", "iqtibos_mos_emas", _("«%(quote)s» manbalarda aynan topilmadi") % {"quote": quote[:120]}))
            continue
        # Iqtibos aynan ko'rsatilgan [M#] manbasidan bo'lsin (boshqa moddadagi gap noto'g'ri havola bilan o'tib ketmasin)
        cited_keys = [k for k in CITE_RE.findall(m.group(3)) if k in corpus]
        if cited_keys and not all(any(p in corpus[k] for k in cited_keys) for p in pieces):
            report.issues.append(Issue("error", "iqtibos_boshqa_manbada", _("«%(quote)s» ko'rsatilgan [%(key)s] manbada emas, boshqa manbada") % {
                "quote": quote[:120], "key": "][".join(cited_keys)}))

    known_numbers = {s.hit.payload.get("article_number") for s in sources if s.hit.payload.get("unit_type") == "ARTICLE"}
    source_texts = " ".join(corpus.values())
    for num in dict.fromkeys(ARTICLE_MENTION_RE.findall(answer)):
        # "6-modda" "16-modda" ichidan topilmasin: raqam oldida boshqa raqam bo'lmasin
        in_texts = re.search(rf"(?<![\d⁰¹²³⁴⁵⁶⁷⁸⁹]){re.escape(num)}-modda", source_texts)
        if num not in known_numbers and not in_texts:
            report.issues.append(Issue("warning", "notanish_modda",
                                       _("%(num)s-modda manbalar orasida yo'q — tekshirish kerak") % {"num": num}))
    return report
