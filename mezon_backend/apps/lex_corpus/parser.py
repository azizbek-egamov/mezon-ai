"""lex.uz hujjat sahifasini (HTML) matn birliklariga (modda / band / butun matn) ajratish.

Sahifa tuzilishi (2026-10 holatiga): `div.lx_elem` larning tekis ketma-ketligi; element turi
lx_elem ning qo'shimcha klassida (CLAUSE_DEFAULT — modda sarlavhasi, ACT_TEXT — matn,
TEXT_HEADER_DEFAULT — qism/bo'lim/bob, BY_DEFAULT — tahrir belgisi, ACT_FORM/ACT_TITLE/
GRIF_PARLAMENT/SIGNATURE/ACT_ESSENTIAL_ELEMENTS — rekvizitlar). Matn `div[id]` ichida,
id — havola uchun element id (`/uz/docs/-111453#-310589`). Modda ichidagi qismlar bo'sh
ACT_TEXT bilan ajratiladi.

Hujjat turlari bo'yicha 4 xil tuzilish uchraydi:
  CLAUSE  — kodekslar: modda sarlavhasi CLAUSE_DEFAULT (yoki TEXT_HEADER_DEFAULT) da;
  INLINE  — o'zgartirish kirituvchi / qisqa qonunlar: "1-modda. ..." ACT_TEXT boshida;
  BAND    — Plenum qarorlari va boshqalar: raqamlangan bandlar "1. ...";
  WHOLE   — moddasiz hujjatlar (masalan, ratifikatsiya qonunlari): butun matn bitta birlik.
"""
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from bs4 import BeautifulSoup, Tag

from .normalize import clean_text

SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
SUP_GAP_RE = re.compile(r"(\d)\s+([⁰¹²³⁴⁵⁶⁷⁸⁹]+)\s*(?=-|\s|$)")
ARTICLE_RE = re.compile(r"^(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)\s*-\s*(?:modda|модда|статья)\b\.?\s*(.*)$", re.I)
# ACT_TEXT ichida faqat "19-modda. ..." (nuqta bilan); "19-modda uchinchi qismining..." — havola, sarlavha emas
INLINE_ARTICLE_RE = re.compile(r"^(?:\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*\s*-\s*(?:modda|модда|статья)|Статья\s+\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)\.(?:\s|$)", re.I)
ARTICLE_RU_RE = re.compile(r"^Статья\s+(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)\.?\s*(.*)$")
BAND_RE = re.compile(r"^(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)\.\s+\S")
# Ichki sarlavha deb hisoblash chegarasi: "1-modda. Ushbu Qonunning maqsadi" (qisqa, nuqtasiz)
INLINE_HEADING_MAX = 150

TEXT_KINDS = ("ACT_TEXT", "TABLE")


class UnitType:
    ARTICLE = "ARTICLE"
    BAND = "BAND"
    PREAMBLE = "PREAMBLE"
    WHOLE = "WHOLE"


@dataclass
class Element:
    elem_id: str
    kind: str
    text: str

    @property
    def is_text(self) -> bool:
        return self.kind.startswith(TEXT_KINDS)


@dataclass
class Article:
    """Matn birligi: modda, band, kirish qismi yoki butun matn."""
    number: str
    heading: str
    elem_id: str
    position: int
    section_path: list[str]
    unit_type: str = UnitType.ARTICLE
    parts: list[dict] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(p["text"] for p in self.parts)


@dataclass
class ParsedDocument:
    title: str
    elements: list[Element]
    articles: list[Article]
    headers: list[Element]
    current_edition: str | None
    editions: list[str]
    structure: str


def _elem_text(body: Tag) -> str:
    for sup in body.find_all("sup"):
        sup.replace_with(sup.get_text().translate(SUPERSCRIPT))
    for br in body.find_all("br"):
        br.replace_with(" ")
    # Element bitta abzas: ichki teglar (a, b, span) matnga bo'shliqsiz qo'shiladi; "18 ¹ -modda" -> "18¹-modda"
    return SUP_GAP_RE.sub(r"\1\2", clean_text(body.get_text("")))


def _kind(div: Tag) -> str:
    kinds = [c for c in div.get("class", []) if c != "lx_elem"]
    return kinds[0] if kinds else ""


EDITION_LABEL_RE = re.compile(r"^\d\d\.\d\d\.\d{4}(?: \d\d)?$")


def edition_label_date(label: str) -> date:
    return datetime.strptime(label[:10], "%d.%m.%Y").date()


def _parse_editions(soup: BeautifulSoup) -> tuple[str | None, list[str]]:
    """Tahrirlar ro'yxati: yorliqlar ('15.10.2026', '15.10.2026 01'); bir kunda bir necha tahrir bo'lishi mumkin."""
    menu = soup.select_one("#lx_var_t")
    if menu is None:
        return None, []
    current, labels = None, []
    for item in menu.select(".dropdown-menu__item"):
        label = " ".join(item.get_text().split())
        if not EDITION_LABEL_RE.match(label):
            continue
        labels.append(label)
        if "lx_date_selected" in item.get("class", []):
            current = label
    return current, labels


OPEN_URL_RE = re.compile(r"openUrl\('/\w+/docs/(-?\d+)'\)")


def parse_language_links(html: str) -> dict[str, str]:
    """Hujjat sarlavhasidagi til almashtirgichi: {'ru': '111457', 'cyr': '111453', 'lat': '-111453'}.
    lex.uz da har bir til versiyasi alohida hujjat (id): lotin — manfiy id, kirill — musbat, rus — boshqa raqam.
    Joriy til versiyasi bosilmaydi (onclick yo'q) — u qaytarilmaydi. Tugma matni: «Рус», «Ўзб», «O’zb»."""
    soup = BeautifulSoup(html, "lxml")
    links: dict[str, str] = {}
    for div in soup.select("div.docContentHeader__item-link[onclick]"):
        m = OPEN_URL_RE.search(div["onclick"])
        label = " ".join(div.get_text().split())
        if not m or not label:
            continue
        if label.startswith("Рус"):
            links["ru"] = m.group(1)
        elif label.startswith("Ўзб"):
            links["cyr"] = m.group(1)
        elif label.lower().startswith(("o’z", "oʻz", "o'z", "oʼz", "ozb", "uzb")):
            links["lat"] = m.group(1)
    return links


def parse_elements(soup: BeautifulSoup) -> list[Element]:
    out = []
    for div in soup.select("div.lx_elem"):
        body = div.find("div", id=True)
        if body is None:
            continue
        out.append(Element(elem_id=body["id"], kind=_kind(div), text=_elem_text(body)))
    return out


def _match_article(text: str):
    return ARTICLE_RE.match(text) or ARTICLE_RU_RE.match(text)


def detect_structure(elements: list[Element]) -> str:
    if any(e.kind in ("CLAUSE_DEFAULT", "TEXT_HEADER_DEFAULT") and _match_article(e.text) for e in elements):
        return "CLAUSE"
    if any(e.is_text and INLINE_ARTICLE_RE.match(e.text) for e in elements):
        return "INLINE"
    if sum(1 for e in elements if e.is_text and BAND_RE.match(e.text)) >= 2:
        return "BAND"
    return "WHOLE"


def _split_inline_heading(rest: str) -> tuple[str, str]:
    """'Ushbu Qonunning maqsadi' -> sarlavha; uzun yoki gap bilan tugagan matn -> mazmun."""
    if rest and len(rest) <= INLINE_HEADING_MAX and not rest.endswith((".", ":", ";", "—", "-", ",")):
        return rest, ""
    return "", rest


def build_articles(elements: list[Element], structure: str | None = None) -> tuple[list[Article], list[Element]]:
    structure = structure or detect_structure(elements)
    articles: list[Article] = []
    headers: list[Element] = []
    section: list[str] = []
    current: Article | None = None
    part: dict | None = None

    def close_part():
        nonlocal part
        if current is not None and part and part["paragraphs"]:
            part["n"] = len(current.parts) + 1
            part["text"] = "\n".join(p["text"] for p in part["paragraphs"])
            current.parts.append(part)
        part = None

    def start(number: str, heading: str, elem_id: str, unit_type: str) -> Article:
        nonlocal current
        close_part()
        current = Article(number=number, heading=heading, elem_id=elem_id, position=len(articles),
                          section_path=list(section), unit_type=unit_type)
        articles.append(current)
        return current

    def add_paragraph(el: Element, text: str | None = None):
        nonlocal part
        if part is None:
            part = {"paragraphs": []}
        part["paragraphs"].append({"elem_id": el.elem_id, "text": el.text if text is None else text})

    for el in elements:
        m = _match_article(el.text) if el.text else None
        if el.kind in ("CLAUSE_DEFAULT", "TEXT_HEADER_DEFAULT") and structure == "CLAUSE" and m:
            start(m.group(1), m.group(2), el.elem_id, UnitType.ARTICLE)
            continue
        if el.kind == "TEXT_HEADER_DEFAULT":
            if el.text:
                close_part()
                current = None
                headers.append(el)
                section = _update_section(section, el.text)
            continue
        if el.kind == "CLAUSE_DEFAULT":
            continue  # bo'sh yoki moddaga mos kelmaydigan sarlavha (masalan JK 227-modda ichida) moddani yopmaydi
        if not el.is_text:
            continue  # BY_DEFAULT, rekvizitlar, imzo
        if not el.text:
            close_part()
            continue
        if structure == "INLINE" and m and INLINE_ARTICLE_RE.match(el.text):
            heading, content = _split_inline_heading(m.group(2))
            start(m.group(1), heading, el.elem_id, UnitType.ARTICLE)
            if content:
                add_paragraph(el)
            continue
        if structure == "BAND" and (b := BAND_RE.match(el.text)):
            start(b.group(1), "", el.elem_id, UnitType.BAND)
            add_paragraph(el)
            continue
        if current is None:
            # Birinchi birlikdan oldingi matn — kirish qismi (preambula); WHOLE da — butun matn.
            start("", "", el.elem_id, UnitType.WHOLE if structure == "WHOLE" else UnitType.PREAMBLE)
        add_paragraph(el)
    close_part()
    if structure == "INLINE":
        # "2-modda. Ushbu Qonun rasmiy eʼlon qilingan kundan eʼtiboran kuchga kiradi" — sarlavha emas, mazmun
        for a in articles:
            if a.unit_type == UnitType.ARTICLE and not a.parts and a.heading:
                a.parts = [{"n": 1, "paragraphs": [{"elem_id": a.elem_id, "text": a.heading}], "text": a.heading}]
                a.heading = ""
    return [a for a in articles if a.parts or a.unit_type == UnitType.ARTICLE], headers


SECTION_LEVELS = [
    re.compile(r"\bQISM\b|\bҚИСМ\b|\bЧАСТЬ\b", re.I),
    re.compile(r"\bBO.LIM\b|\bБЎЛИМ\b|\bРАЗДЕЛ\b", re.I),
    re.compile(r"^[IVXLC]+\s+bob\b|^[IVXLC]+\s+боб\b|\bbob\b|\bбоб\b|\bбап\b|\bГлава\b", re.I),
]


def _update_section(section: list[str], header: str) -> list[str]:
    for level, rx in enumerate(SECTION_LEVELS):
        if rx.search(header):
            return section[:level] + [header]
    return section + [header]


def parse_document(html: str) -> ParsedDocument:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one("div.ACT_TITLE div[id]")
    title = _elem_text(title_el) if title_el else ""
    current, editions = _parse_editions(soup)
    elements = parse_elements(soup)
    structure = detect_structure(elements)
    articles, headers = build_articles(elements, structure)
    return ParsedDocument(title=title, elements=elements, articles=articles, headers=headers,
                          current_edition=current, editions=editions, structure=structure)
