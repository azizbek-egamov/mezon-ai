"""Qonunchilik korpusi modellari (TZ v2.1 §7.3)."""
from urllib.parse import quote

from django.db import models


class DocType(models.TextChoices):
    CONSTITUTION = "CONSTITUTION", "Konstitutsiya"
    CONST_LAW = "CONST_LAW", "Konstitutsiyaviy qonun"
    CODE = "CODE", "Kodeks"
    LAW = "LAW", "Qonun"
    PLENUM = "PLENUM", "Plenum qarori"
    COURT = "COURT", "Sud qarori (Konstitutsiyaviy sud, sudlov hay'ati)"
    PRES_DECREE = "PRES_DECREE", "Prezident farmoni"
    PRES_RESOLUTION = "PRES_RESOLUTION", "Prezident qarori"
    VMQ = "VMQ", "Vazirlar Mahkamasi qarori"
    PARLIAMENT = "PARLIAMENT", "Oliy Majlis / palatalar qarori"
    MINISTRY = "MINISTRY", "Idoraviy hujjat"
    LOCAL = "LOCAL", "Mahalliy hujjat"
    INTL_TREATY = "INTL_TREATY", "Xalqaro shartnoma"
    OTHER = "OTHER", "Boshqa"


class Status(models.TextChoices):
    ACTIVE = "ACTIVE", "Amalda"
    REPEALED = "REPEALED", "Kuchini yo'qotgan"
    NOT_IN_FORCE = "NOT_IN_FORCE", "Kuchga kirmagan"


# Matn tillari (TZ §5.4): o'zbek lotin / kirill va rus — lex.uz da har biri alohida hujjat (id) sifatida turadi.
LANGS = ("lat", "cyr", "ru")
LANG_FIELDS = {"lat": "content_uz_lat", "cyr": "content_uz_cyr", "ru": "content_ru"}
LANG_LABELS = {"lat": "Oʻzbekcha (lotin)", "cyr": "Ўзбекча (кирилл)", "ru": "Русский"}
# Interfeys tili (i18n kodi) -> korpus matni tili. Qoraqalpoq va ingliz tillarida rasmiy matn yo'q (TZ §5.4) —
# iqtibos o'zbek lotinida keltiriladi.
UI_TO_CORPUS_LANG = {"uz-Latn": "lat", "uz-Latn-2026": "lat", "uz-Cyrl": "cyr", "ru": "ru", "kaa": "lat", "en": "lat"}


def corpus_lang(ui_lang: str | None) -> str:
    return UI_TO_CORPUS_LANG.get(ui_lang or "", "lat")


class CorpusTier(models.TextChoices):
    CORE = "CORE", "Yadro"
    EXTENDED = "EXTENDED", "Kengaytirilgan"
    ON_DEMAND = "ON_DEMAND", "So'rov bo'yicha"


class LegalActDocument(models.Model):
    abs_id = models.BigIntegerField(primary_key=True, help_text="abs(lex.uz id)")
    lex_id_lat = models.CharField(max_length=16, blank=True)
    lex_id_cyr = models.CharField(max_length=16, blank=True)
    lex_id_ru = models.CharField(max_length=16, blank=True, help_text="Rus tilidagi versiya id si (lex.uz da alohida hujjat)")
    doc_type = models.CharField(max_length=20, choices=DocType.choices, db_index=True)
    act_type_raw = models.TextField(blank=True)
    hierarchy_weight = models.FloatField()
    official_number = models.CharField(max_length=100, blank=True, db_index=True)
    adoption_date = models.DateField(null=True, blank=True, db_index=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    title_uz_lat = models.TextField(blank=True)
    title_uz_cyr = models.TextField(blank=True)
    title_ru = models.TextField(blank=True)
    title_search = models.TextField(blank=True, help_text="Normallashtirilgan lotin sarlavha (qidiruv uchun)")
    status = models.CharField(max_length=16, choices=Status.choices, db_index=True)
    is_amending = models.BooleanField(default=False, db_index=True)
    corpus_tier = models.CharField(max_length=10, choices=CorpusTier.choices, db_index=True)
    content_hash = models.CharField(max_length=64, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    history_from = models.DateField(null=True, blank=True,
                                    help_text="Moddalar tahrirlari tarixi shu sanadan boshlab yuklangan (bo'sh — tarix yo'q)")
    translations = models.JSONField(default=dict, blank=True, help_text=(
        "Boshqa til versiyalari holati: {'cyr': {lex_id, edition, matched, total, stale, fetched_at}, 'ru': {...}}"))

    class Meta:
        ordering = ["-adoption_date"]

    def __str__(self):
        return f"{self.abs_id} {self.title_uz_lat or self.title_uz_cyr or self.title_ru}"[:120]

    @property
    def primary_lex_id(self) -> str:
        return self.lex_id_lat or self.lex_id_cyr or f"-{self.abs_id}"

    def lex_id_for(self, lang: str) -> str:
        """Til versiyasining lex.uz id si; bo'sh — bu tilda versiya yo'q."""
        return {"lat": self.lex_id_lat, "cyr": self.lex_id_cyr, "ru": self.lex_id_ru}[lang]

    def title_for(self, lang: str) -> str:
        """Hujjat nomi shu tilda; yo'q bo'lsa — bor tildagi nom."""
        own = {"lat": self.title_uz_lat, "cyr": self.title_uz_cyr, "ru": self.title_ru}[lang]
        return own or self.title_uz_lat or self.title_uz_cyr or self.title_ru

    def has_lang(self, lang: str) -> bool:
        """Hujjatning shu tilda to'liq moddalari bazada bormi (tarjima moslashtirilgan va rad etilmagan)."""
        info = self.translations.get(lang)
        return bool(info and info.get("matched") and not info.get("rejected"))


class LegalActEdition(models.Model):
    document = models.ForeignKey(LegalActDocument, on_delete=models.CASCADE, related_name="editions")
    edition_label = models.CharField(max_length=20, blank=True,
                                     help_text="lex.uz tahrir yorlig'i: '15.10.2026' yoki '15.10.2026 01' (ONDATE qiymati)")
    edition_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    source_url = models.CharField(max_length=300)
    content_hash = models.CharField(max_length=64, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("document", "edition_label")]


class LegalActArticle(models.Model):
    document = models.ForeignKey(LegalActDocument, on_delete=models.CASCADE, related_name="articles")
    edition = models.ForeignKey(LegalActEdition, on_delete=models.CASCADE, related_name="articles")
    position = models.PositiveIntegerField(help_text="Hujjat ichidagi tartib raqami")
    unit_type = models.CharField(max_length=10, default="ARTICLE",
                                 choices=[("ARTICLE", "Modda"), ("BAND", "Band"), ("PREAMBLE", "Kirish qismi"),
                                          ("WHOLE", "Butun matn")])
    article_number = models.CharField(max_length=50, blank=True, db_index=True,
                                      help_text="'168', '125¹'; band uchun band raqami")
    heading = models.TextField(blank=True)
    section_path = models.TextField(blank=True, help_text="Qism / bo'lim / bob sarlavhalari")
    content_uz_lat = models.TextField(blank=True)
    content_uz_cyr = models.TextField(blank=True)
    content_ru = models.TextField(blank=True)
    source_lang = models.CharField(max_length=3, default="lat", help_text=(
        "`heading`, `parts`, `section_path`, `lex_elem_id` qaysi tilda ('lat', 'cyr', 'ru'); qolgan tillar `i18n` da"))
    i18n = models.JSONField(default=dict, blank=True, help_text=(
        "Boshqa til versiyalari: {'cyr': {heading, parts, section_path, elem_id}, 'ru': {...}}; "
        "matn `content_*` maydonlarida"))
    parts = models.JSONField(default=list, help_text="[{n, elem_ids, text}] — qismlar va ularning lex.uz element id lari")
    lex_elem_id = models.CharField(max_length=32)
    unit_key = models.CharField(max_length=64, blank=True, db_index=True,
                                help_text="Tahrirlar orasida barqaror kalit: 'ARTICLE:168#1' (birlik turi, raqam, takror tartibi)")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    qdrant_point_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["document", "edition", "position"]
        indexes = [models.Index(fields=["document", "article_number"])]

    def __str__(self):
        return f"{self.article_number}-modda. {self.heading}"

    @property
    def direct_lex_url(self) -> str:
        """Joriy tahrir — oddiy havola; tarixiy versiya — o'sha tahrir sahifasiga (?ONDATE=)."""
        url = f"https://lex.uz/uz/docs/{self.document.primary_lex_id}"
        if not self.edition.is_current:
            url += f"?ONDATE={quote(self.edition.edition_label)}"
        return f"{url}#{self.lex_elem_id}"

    @property
    def primary_text(self) -> str:
        """Moddaning asosiy (yuklangan) tilidagi matni."""
        return (self.text_in(self.source_lang) or self.content_uz_lat or self.content_uz_cyr or self.content_ru)

    def text_in(self, lang: str) -> str:
        return getattr(self, LANG_FIELDS[lang])

    def has_lang(self, lang: str) -> bool:
        return bool(self.text_in(lang))

    def _lang_data(self, lang: str) -> dict:
        return {} if lang == self.source_lang else self.i18n.get(lang) or {}

    def heading_in(self, lang: str) -> str:
        return self.heading if lang == self.source_lang else self._lang_data(lang).get("heading", "")

    def parts_in(self, lang: str) -> list[dict]:
        return self.parts if lang == self.source_lang else self._lang_data(lang).get("parts", [])

    def section_in(self, lang: str) -> str:
        return self.section_path if lang == self.source_lang else self._lang_data(lang).get("section_path", "")

    def elem_id_in(self, lang: str) -> str:
        return self.lex_elem_id if lang == self.source_lang else self._lang_data(lang).get("elem_id", "")

    def lang_label(self, lang: str) -> str:
        """Iqtibos yorlig'i shu tilda: '168-modda. Firibgarlik' / '168-модда. …' / 'Статья 168. …'."""
        heading, number = self.heading_in(lang), self.article_number
        if self.unit_type == "ARTICLE":
            return (f"Статья {number}. {heading}" if lang == "ru"
                    else f"{number}-{'модда' if lang == 'cyr' else 'modda'}. {heading}").strip()
        if self.unit_type == "BAND":
            return {"lat": f"{number}-band", "cyr": f"{number}-банд", "ru": f"Пункт {number}"}[lang]
        if self.unit_type == "PREAMBLE":
            return {"lat": "Kirish qismi", "cyr": "Кириш қисми", "ru": "Вводная часть"}[lang]
        return ""

    def url_in(self, lang: str) -> str:
        """Shu til versiyasidagi havola (joriy tahrir — oddiy; tarixiy — ?ONDATE=)."""
        lex_id = self.document.lex_id_for(lang) if lang != self.source_lang else self.document.primary_lex_id
        if not lex_id:
            return self.direct_lex_url
        url = f"https://lex.uz/uz/docs/{lex_id}"
        if not self.edition.is_current:
            url += f"?ONDATE={quote(self.edition.edition_label)}"
        return f"{url}#{self.elem_id_in(lang) or self.lex_elem_id}"

    def is_valid_on(self, day) -> bool:
        return (self.valid_from is None or self.valid_from <= day) and (self.valid_until is None or day <= self.valid_until)


class SyncRun(models.Model):
    """lex.uz sinxronizatsiyasining bitta ishga tushirilishi (TZ §6.4, §9.2 SuperAdmin: sinxronizatsiya holati)."""

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Bajarilmoqda"
        OK = "OK", "Muvaffaqiyatli"
        PARTIAL = "PARTIAL", "Xatolar bilan"
        FAILED = "FAILED", "Xato"

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    stats = models.JSONField(default=dict, blank=True,
                             help_text="Yangi hujjatlar, maqomi o'zgarganlar, qayta yuklangan va indekslangan hujjatlar")
    log = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "lex.uz sinxronizatsiyasi"
        verbose_name_plural = "lex.uz sinxronizatsiyalari"

    def __str__(self):
        return f"{self.started_at:%d.%m.%Y %H:%M} — {self.get_status_display()}"
