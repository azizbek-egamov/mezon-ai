"""lex.uz metadata normallashtirish: yozuv, apostroflar, homogliflar, hujjat turi (TZ v2.1 §6.3)."""
import re

from .models import CorpusTier, DocType, Status

CYR_RE = re.compile(r"[Ѐ-ӿ]")
LAT_RE = re.compile(r"[A-Za-z]")

# Konstitutsiyalar reyestrda turi va sanasisiz keladi (TAHLIL.md).
CONSTITUTION_IDS = {6445145, 20596}
KARAKALPAK_CONSTITUTION_ID = 4953674

HIERARCHY_WEIGHT = {
    DocType.CONSTITUTION: 1.00,
    DocType.CONST_LAW: 0.95,
    DocType.CODE: 0.95,
    DocType.LAW: 0.90,
    DocType.PLENUM: 0.85,
    DocType.COURT: 0.80,
    DocType.PRES_DECREE: 0.80,
    DocType.PRES_RESOLUTION: 0.75,
    DocType.VMQ: 0.70,
    DocType.MINISTRY: 0.65,
    DocType.PARLIAMENT: 0.65,
    DocType.INTL_TREATY: 0.65,
    DocType.LOCAL: 0.60,
    DocType.OTHER: 0.60,
}
CORE_TYPES = {DocType.CONSTITUTION, DocType.CONST_LAW, DocType.CODE, DocType.LAW, DocType.PLENUM}
EXTENDED_TYPES = {DocType.PRES_DECREE, DocType.PRES_RESOLUTION, DocType.VMQ, DocType.COURT}

# Lotin so'z ichidagi kirill homogliflar -> lotin.
HOMOGLYPHS = str.maketrans("аеорсухіјАВЕКМНОРСТХІЈ", "aeopcyxijABEKMHOPCTXIJ")
TO_TURNED_COMMA = "ʻ"  # ʻ  (oʻ, gʻ)
TO_APOSTROPHE = "ʼ"    # ʼ  (tutuq belgisi)
APOS_RE = re.compile(r"([OoGg])['`‘’ʼʻ]|['`‘’ʻʼ]")


def detect_script(text: str) -> str:
    """'cyr' yoki 'lat' — harflar soni bo'yicha."""
    return "cyr" if len(CYR_RE.findall(text)) > len(LAT_RE.findall(text)) else "lat"


def is_russian(text: str) -> bool:
    """Kirill matnda o'zbekcha harflar (ў қ ғ ҳ) bo'lmasa — rus tili deb hisoblanadi."""
    return detect_script(text) == "cyr" and not re.search(r"[ўқғҳЎҚҒҲ]", text)


def text_lang(text: str) -> str:
    """Matn tili: 'lat' (o'zbek lotin), 'cyr' (o'zbek kirill) yoki 'ru' (rus)."""
    if detect_script(text) == "lat":
        return "lat"
    return "ru" if is_russian(text) else "cyr"


def normalize_apostrophes(text: str) -> str:
    return APOS_RE.sub(lambda m: m.group(1) + TO_TURNED_COMMA if m.group(1) else TO_APOSTROPHE, text)


def fix_homoglyphs(text: str) -> str:
    """Asosan lotin bo'lgan so'zlardagi kirill harflarni lotinga almashtiradi ('pаrlаmеnt' -> 'parlament')."""
    def fix(word: str) -> str:
        if CYR_RE.search(word) and LAT_RE.search(word) and len(LAT_RE.findall(word)) >= len(CYR_RE.findall(word)):
            return word.translate(HOMOGLYPHS)
        return word
    return re.sub(r"\S+", lambda m: fix(m.group(0)), text)


def clean_text(text: str) -> str:
    text = text.replace("\u200e", "").replace("\uf020", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(text: str) -> str:
    return normalize_apostrophes(fix_homoglyphs(clean_text(text)))


AMENDING_RE = re.compile(
    r"o.zgartish|o.zgartirish|qo.shimcha|kuchini yo.qotgan|"
    r"ўзгартиш|ўзгартириш|қўшимча|кучини йўқотган|изменени|дополнени|утратившим",
    re.IGNORECASE,
)


def is_amending(title: str) -> bool:
    return bool(AMENDING_RE.search(title))


def _has(t: str, *keys: str) -> bool:
    return any(k in t for k in keys)


def classify_doc_type(abs_id: int, act_type: str, title: str, act_number: str) -> str:
    t = normalize_title(act_type).lower().replace(TO_TURNED_COMMA, "'")
    num = act_number.upper()
    if abs_id in CONSTITUTION_IDS:
        return DocType.CONSTITUTION
    if abs_id == KARAKALPAK_CONSTITUTION_ID:
        return DocType.LOCAL
    if _has(t, "konstitutsiyaviy qonun", "конституциявий қонун", "конституционный закон"):
        return DocType.CONST_LAW
    if _has(t, "plenum", "пленум"):
        return DocType.PLENUM
    if _has(t, "konstitutsiyaviy sud", "конституциявий суд", "конституционного суда", "sudlov hay'at",
            "судлов ҳайъат", "oliy sudi", "oliy xo'jalik sudi", "олий суди"):
        return DocType.COURT
    if _has(t, "qoraqalpog'iston", "қорақалпоғистон", "каракалпакстан", "xalq deputatlari", "халқ депутатлари",
            "hokim", "ҳоким", "хоким"):
        return DocType.LOCAL
    if re.search(r"\bkodeksi\b|\bкодекси\b|\bкодекс\b", t) and not _has(t, "axloq", "xalqaro"):
        return DocType.CODE
    if _has(t, "qonuni", "қонуни") or re.search(r"\bзакон\b", t):
        return DocType.LAW
    if _has(t, "prezident", "президент"):
        if _has(t, "farmoni", "фармони", "указ"):
            return DocType.PRES_DECREE
        return DocType.PRES_RESOLUTION
    if _has(t, "vazirlar mahkamasi", "вазирлар маҳкамаси", "кабинет"):
        return DocType.VMQ
    if _has(t, "oliy majlis", "олий мажлис", "senat", "сенат", "qonunchilik palata", "қонунчилик палата",
            "oliy kengash", "олий кенгаш", "законодательн"):
        return DocType.PARLIAMENT
    if _has(t, "bitim", "битим", "shartnoma", "шартнома", "konvensiya", "конвенция", "protokol", "протокол",
            "memorandum", "agreement", "соглашени", "договор", "konventsiya"):
        return DocType.INTL_TREATY
    if _has(t, "vazir", "вазир", "qo'mita", "қўмита", "агентств", "agentlig", "markaziy bank", "марказий банк",
            "inspeksiya", "инспекция", "buyrug'i", "буйруғи", "приказ", "standart", "стандарт", "bojxona",
            "xizmati", "хизмати", "комитет", "министерств", "palatasi", "komissiya", "комиссия"):
        return DocType.MINISTRY
    # act_type yo'q yoki axlat bo'lsa — raqam formati bo'yicha.
    if num.startswith("PF-") or num.startswith("ПФ-"):
        return DocType.PRES_DECREE
    if num.startswith("PQ-") or num.startswith("ПҚ-") or num.startswith("ПП-"):
        return DocType.PRES_RESOLUTION
    if num.startswith(("O'RQ-", "OʻRQ-", "ЎРҚ-", "ZRU-", "ЗРУ-")):
        return DocType.LAW
    return DocType.OTHER


def map_status(raw: str) -> str:
    return Status.ACTIVE if raw == "kuchda" else Status.REPEALED


def corpus_tier(doc_type: str, status: str) -> str:
    if status == Status.ACTIVE and doc_type in CORE_TYPES:
        return CorpusTier.CORE
    if status == Status.ACTIVE and doc_type in EXTENDED_TYPES:
        return CorpusTier.EXTENDED
    return CorpusTier.ON_DEMAND
