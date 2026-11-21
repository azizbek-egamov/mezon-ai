"""Oʻzbek lotin ↔ kirill deterministik transliteratsiyasi (TZ §5.4: "AI faqat bitta yozuvda yozadi; ikkinchisi
deterministik transliteratsiya bilan hosil qilinadi").

Qoidalar — 1995 yil lotin alifbosi va kirill alifbosi mosligi. Bir ma'noli bo'lmagan joylar:
  * lotin "e" so'z boshida → "э" (Эргашев, экспертиза), boshqa joyda → "е" (Тошкент → "Toshkent" emas, "Тошкент");
  * lotin "ts" faqat so'z boshida va "-tsiya/-tsion/-tsial/-tsent" o'zlashma qo'shimchalarida → "ц";
  * lotin "yo", "yu", "ya", "ye" → ё, ю, я, е; oy nomlari (sentabr → сентябр) lug'atdan;
  * kirill "е" so'z boshida va unlidan keyin → "ye", boshqa joyda "e"; "ь" tushiriladi, "щ" → "shch".
Rasmiy (lex.uz) iqtiboslar bundan mustasno — ular tayyor matndan olinadi; bu modul interfeys va AI javobi uchun.
"""
import re

from apps.lex_corpus.normalize import normalize_apostrophes

CYR_VOWELS = "аеёиоуэюяўыАЕЁИОУЭЮЯЎЫ"
WORD_RE = re.compile(r"[A-Za-zʻʼА-Яа-яЁёЎўҚқҒғҲҳ]+")

# Lotin -> kirill istisnolari (butun so'z, kichik harfda).
LAT_WORDS = {"sentabr": "сентябр", "oktabr": "октябр", "noyabr": "ноябр", "dekabr": "декабр"}

# Lotin birikmalari (uzunlari oldin); natija kirill harf(lar): "yoʻl" -> "йўл" ("yo" -> "ё" dan oldin).
_LAT_DIGRAPHS = [("yoʻ", "йў"), ("oʻ", "ў"), ("gʻ", "ғ"), ("sh", "ш"), ("ch", "ч"), ("yo", "ё"), ("yu", "ю"), ("ya", "я"),
                 ("ye", "е")]
_LAT_SINGLE = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ", "i": "и", "j": "ж", "k": "к", "l": "л",
    "m": "м", "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в", "x": "х",
    "y": "й", "z": "з", "ʼ": "ъ",
}
_TS_SUFFIX = ("iya", "iyal", "ion", "ial", "ent", "ess", "edur")

_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "ʼ", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "oʻ",
    "қ": "q", "ғ": "gʻ", "ҳ": "h", "ё": "yo", "е": "e",
}


def _upper_like(src: str, out: str) -> str:
    return out.upper() if src[:1].isupper() else out


def _word_lat_to_cyr(word: str) -> str:
    lower = word.lower()
    if lower in LAT_WORDS:
        cyr = LAT_WORDS[lower]
        return cyr.upper() if word.isupper() else cyr.capitalize() if word[:1].isupper() else cyr
    res: list[str] = []
    i = 0
    while i < len(word):
        low = lower[i:]
        if low.startswith("ts") and (i == 0 or low[2:].startswith(_TS_SUFFIX)):
            piece, out = word[i:i + 2], "ц"
        else:
            for lat, cyr in _LAT_DIGRAPHS:
                if low.startswith(lat):
                    piece, out = word[i:i + len(lat)], cyr
                    break
            else:
                piece = word[i]
                out = _LAT_SINGLE.get(low[0], piece)
                if low[0] == "e" and i == 0:
                    out = "э"
        res.append(_upper_like(piece, out))
        i += len(piece)
    return "".join(res)


def lat_to_cyr(text: str) -> str:
    """Oʻzbek lotin matni -> kirill."""
    text = normalize_apostrophes(text)
    return WORD_RE.sub(lambda m: _word_lat_to_cyr(m.group(0)), text)


def cyr_to_lat(text: str) -> str:
    """Oʻzbek kirill matni -> lotin."""
    out: list[str] = []
    for idx, ch in enumerate(text):
        low = ch.lower()
        if low not in _CYR_TO_LAT:
            out.append(ch)
            continue
        lat = _CYR_TO_LAT[low]
        prev = text[idx - 1] if idx else ""
        if low == "е" and (not prev.isalpha() or prev in CYR_VOWELS or prev in "ъьЪЬ"):
            lat = "ye"
        if ch.isupper() and lat:
            nxt = text[idx + 1] if idx + 1 < len(text) else ""
            all_caps = len(lat) > 1 and (nxt.isupper() or prev.isupper())
            lat = lat.upper() if all_caps else lat[0].upper() + lat[1:]
        out.append(lat)
    return normalize_apostrophes("".join(out))


# --- 2026-yilgi Yangi Oʻzbek Lotin Alifbosi (Isloh qilingan 28 harf + tutuq belgisi) ---
# Oʻzgarishlar: Gʻ/gʻ -> Ğ/ğ, Oʻ/oʻ -> Ö/ö, Sh/sh -> Ş/ş, Ch/ch -> Ç/ç. Tutuq belgisi (ʼ) oʻzgarishsiz qoladi.
_PROTECT_RE = re.compile(r"(%\(\w+\)s|%[sd]|<[^>]+>|&\w+;|{{\s*\w+\s*}})")


def lat_to_new_latn(text: str) -> str:
    """Eski lotin (1995) -> 2026 yangi lotin alifbosi.
    Oʻrinbosarlar (%(n)s, {{count}}) va HTML teglar himoyalangan holda qoladi.
    """
    if not text:
        return ""
    parts = _PROTECT_RE.split(text)

    def _convert_piece(s: str) -> str:
        s = normalize_apostrophes(s)
        # Gʻ -> Ğ, gʻ -> ğ, Oʻ -> Ö, oʻ -> ö
        s = s.replace("Gʻ", "Ğ").replace("gʻ", "ğ")
        s = s.replace("Oʻ", "Ö").replace("oʻ", "ö")
        # Sh / sh -> Ş / ş
        s = re.sub(r"SH(?=[A-ZÖĞŞÇ])|(?<=[A-ZÖĞŞÇ])SH|\bSH\b", "Ş", s)
        s = re.sub(r"Sh|SH", "Ş", s)
        s = re.sub(r"sh", "ş", s)
        # Ch / ch -> Ç / ç
        s = re.sub(r"CH(?=[A-ZÖĞŞÇ])|(?<=[A-ZÖĞŞÇ])CH|\bCH\b", "Ç", s)
        s = re.sub(r"Ch|CH", "Ç", s)
        s = re.sub(r"ch", "ç", s)
        return s

    return "".join(part if idx % 2 == 1 else _convert_piece(part) for idx, part in enumerate(parts))


def new_latn_to_lat(text: str) -> str:
    """2026 yangi lotin -> eski lotin (1995) alifbosi (qaytarish)."""
    if not text:
        return ""
    parts = _PROTECT_RE.split(text)

    def _convert_piece(s: str) -> str:
        s = s.replace("Ğ", "Gʻ").replace("ğ", "gʻ")
        s = s.replace("Ö", "Oʻ").replace("ö", "oʻ")
        # Ş -> SH / Sh / ş -> sh
        s = re.sub(r"Ş(?=[A-Z])|(?<=[A-Z])Ş", "SH", s)
        s = s.replace("Ş", "Sh").replace("ş", "sh")
        # Ç -> CH / Ch / ç -> ch
        s = re.sub(r"Ç(?=[A-Z])|(?<=[A-Z])Ç", "CH", s)
        s = s.replace("Ç", "Ch").replace("ç", "ch")
        return s

    return "".join(part if idx % 2 == 1 else _convert_piece(part) for idx, part in enumerate(parts))

