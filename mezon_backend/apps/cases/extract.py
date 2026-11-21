"""Ish hujjatlaridan faktlarni ajratish (TZ §4.1, Agent-1 Fact Extractor) va iqtiboslarni tekshirish.

Hujjat 5 sahifalik bloklarga bo'linadi (map). Har bir blok uchun LLM faktlar ro'yxatini JSON da qaytaradi:
har bir fakt — sahifa raqami va shu sahifadan AYNAN ko'chirilgan iqtibos bilan. Keyin kod har bir iqtibos
ko'rsatilgan sahifada (yoki chegara holatida qo'shni sahifada) so'zma-so'z borligini tekshiradi.
"""
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

from apps.lex_corpus.normalize import normalize_apostrophes
from apps.rag.llm import get_llm, task_model

from .case_types import adapt_extract, get_case_type
from .pdf_text import Page

logger = logging.getLogger(__name__)

BLOCK_PAGES = 5
FACT_TYPES = ["event", "statement", "amount", "procedural_action", "document_detail", "person"]

SYSTEM = """Sen tergov va sud hujjatlarini tahlil qiluvchi tajribali advokat yordamchisisan.
Senga jinoyat ishidan bir nechta sahifa beriladi (<sahifa n="..."> ichida). Matn oʻzbek (lotin yoki kirill) yoki rus tilida boʻlishi mumkin.
Undan ishni tahlil qilish uchun muhim BARCHA faktlarni ajrat: voqealar, koʻrsatmalar (kim nima degan), summalar, sanalar va vaqtlar,
protsessual harakatlar (ushlab turish, tintuv, soʻroq, ekspertiza, qarorlar, tanishtirish, iltimosnomalar va ularning sanasi/vaqti),
hujjat tafsilotlari (bank yozuvlari, telefon maʼlumotlari, chiptalar), shaxslar va ularning roli.
Qoidalar:
- Har bir fakt alohida boʻlsin; bir xil fakt turli shaxslar tomonidan aytilgan boʻlsa — har birini alohida yoz (kim aytgani muhim).
- Jadval, bank koʻchirmasi, telefon maʼlumoti va roʻyxatlarning HAR BIR QATORI alohida fakt (kirim ham, chiqim ham,
  boshlangʻich va oxirgi qoldiq ham) — summalarni oʻzaro solishtirish uchun hech biri tushib qolmasin.
- quote — shu sahifadagi matndan AYNAN koʻchirilgan, faktni tasdiqlovchi qisqa parcha (10-35 soʻz). Soʻzlarni oʻzgartirma, tarjima qilma, qisqartirma.
- page — iqtibos olingan sahifa raqami.
- date — YYYY-MM-DD (nomaʼlum boʻlsa ""), time — HH:MM (nomaʼlum boʻlsa "").
- source — fakt qaysi hujjatdan va kimning soʻzi (masalan: "Jabrlanuvchining soʻroq bayonnomasi — M.A. Qodirova").
- summary — faktning oʻzbek (lotin) tilidagi qisqa mazmuni (1 gap), raqam va vaqtlarni aniq yoz.
- <JSHSHIR_1>, <TEL_2> kabi belgilar — niqoblangan shaxsiy maʼlumotlar, ularni oʻzgartirmasdan qoldir.
Faqat JSON qaytar."""

SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": FACT_TYPES},
                    "page": {"type": "integer"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "source": {"type": "string"},
                    "summary": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["type", "page", "date", "time", "source", "summary", "quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["facts"],
    "additionalProperties": False,
}


@dataclass
class Fact:
    id: str
    type: str
    page: int
    date: str
    time: str
    source: str
    summary: str
    quote: str
    verified: bool = False
    verified_page: int | None = None  # iqtibos aslida topilgan sahifa

    def to_dict(self) -> dict:
        return asdict(self)


def _norm(text: str) -> str:
    text = normalize_apostrophes(text).replace("…", "...")
    text = re.sub(r"[“”„«»\"]", '"', text)
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_quote(fact: Fact, pages_by_no: dict[int, str]) -> None:
    """Iqtibos ko'rsatilgan sahifada (yoki qo'shni sahifada — matn sahifa chegarasidan o'tishi mumkin) bormi."""
    q = _norm(fact.quote).strip(" .,;:")
    pieces = [p.strip(" .,;:") for p in q.split("...") if len(p.strip()) >= 6]
    if not pieces:
        return
    for page_no in (fact.page, fact.page - 1, fact.page + 1):
        text = pages_by_no.get(page_no)
        if text and all(p in _norm(text) for p in pieces):
            fact.verified, fact.verified_page = True, page_no
            return


def _blocks(pages: list[Page], size: int = BLOCK_PAGES) -> list[list[Page]]:
    return [pages[i:i + size] for i in range(0, len(pages), size)]


def _render_block(block: list[Page]) -> str:
    return "\n\n".join(f'<sahifa n="{p.number}">\n{p.text}\n</sahifa>' for p in block)


def extract_block(block: list[Page], model: str | None = None, case_type: str = "criminal") -> list[dict]:
    data = get_llm().chat_json(adapt_extract(SYSTEM, get_case_type(case_type)), _render_block(block), schema=SCHEMA, effort="low", max_tokens=16000,
                               model=model or task_model("extract"))
    pages = {p.number for p in block}
    return [f for f in data.get("facts", []) if f.get("page") in pages]


def extract_facts(pages: list[Page], model: str | None = None, workers: int = 4,
                  on_progress=None, case_type: str = "criminal") -> tuple[list[Fact], list[str]]:
    """Bloklar parallel (API), natija sahifa tartibida; har bir fakt iqtibosi tekshiriladi.
    on_progress(tayyor, jami) — har bir blok tugaganda. Qaytaradi: (faktlar, xato bergan bloklar ro'yxati)."""
    blocks = _blocks([p for p in pages if not p.is_empty])
    done = [0]
    lock = threading.Lock()

    def run(block):
        result = _safe_extract(block, model, case_type)
        if on_progress:
            with lock:
                done[0] += 1
                on_progress(done[0], len(blocks))
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run, blocks))
    pages_by_no = {p.number: p.text for p in pages}
    facts: list[Fact] = []
    errors = [err for _, err in results if err]
    for raw in (f for block_facts, _ in results for f in block_facts):
        fact = Fact(id=f"F{len(facts) + 1}", **{k: raw[k] for k in ("type", "page", "date", "time", "source",
                                                                       "summary", "quote")})
        verify_quote(fact, pages_by_no)
        facts.append(fact)
    return facts, errors


def _safe_extract(block: list[Page], model: str | None, case_type: str = "criminal") -> tuple[list[dict], str | None]:
    try:
        return extract_block(block, model, case_type), None
    except Exception as e:  # bitta blok xatosi butun tahlilni to'xtatmasin — hisobotda ko'rinadi
        logger.error("Blok %s–%s faktlarini ajratib bo'lmadi: %s", block[0].number, block[-1].number, e)
        # Hisobotga (foydalanuvchiga) faqat umumiy xabar: xato matnida URL/kalit/ichki manzil bo'lishi mumkin — u logda
        return [], f"{block[0].number}–{block[-1].number}-varaqlar: faktlarni ajratib boʻlmadi (texnik xato)"
