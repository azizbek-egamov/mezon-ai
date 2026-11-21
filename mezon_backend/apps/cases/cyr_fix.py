"""Oʻzbek kirill OCR matnidagi ў қ ғ ҳ ni lug'at bo'yicha tiklash (9-bosqich).

RapidOCR ning kirill modeli lug'atida o'zbekcha harflar yo'q (ўқув → укув, гувоҳ → гувох). Tuzatish deterministik,
LLM siz: lex.uz dagi o'zbek kirill matnlaridan (`LegalActArticle.content_uz_cyr`) so'z chastotalari lug'ati
tuziladi. Tarkibida у к г х bor so'z uchun bularni ў қ ғ ҳ ga almashtirishdan hosil bo'lgan variantlar ko'riladi;
variant lug'atda yetarlicha uchrasa va asl so'z lug'atda yo'q (yoki ancha kam uchraydigan) bo'lsa — almashtiriladi.

Faqat o'zbekcha deb topilgan sahifalarga qo'llanadi (so'zlarning kamida `UZBEK_SHARE` qismi lug'atda yoki tuzatilgach
lug'atda bo'ladi) — rus matnidagi "хор", "кон" kabi so'zlar buzilmasin. Ismlar va lug'atda yo'q so'zlar o'zgarmaydi,
shuning uchun sahifa baribir ogohlantirish bilan belgilanadi.
"""
import json
import re
from collections import Counter
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from django.conf import settings

SWAP = {"у": "ў", "к": "қ", "г": "ғ", "х": "ҳ"}
WORD_RE = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]+")
MAX_SWAPS = 6          # bir so'zda ko'pi bilan shuncha o'rinni almashtirish variantlari ko'riladi (2^6)
MIN_FREQ = 3           # variant lug'atda kamida shuncha uchragan bo'lishi kerak
DOMINANCE = 20         # asl so'z ham lug'atda bo'lsa: variant undan shuncha marta ko'p uchrashi kerak
UZBEK_SHARE = 0.4
MIN_WORD_LEN = 3


def vocab_path() -> Path:
    return Path(settings.DATA_DIR) / "cache" / "uz_cyr_vocab.json"


def build_vocab() -> Counter:
    """Korpusdagi o'zbek kirill matnlaridan so'z chastotalari."""
    from apps.lex_corpus.models import LegalActArticle

    counts: Counter = Counter()
    qs = LegalActArticle.objects.filter(edition__is_current=True).exclude(content_uz_cyr="")
    for text in qs.values_list("content_uz_cyr", flat=True).iterator(chunk_size=2000):
        counts.update(w.lower() for w in WORD_RE.findall(text))
    return counts


def save_vocab(counts: Counter, path: Path | None = None) -> Path:
    path = path or vocab_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = {w: n for w, n in counts.items() if n >= 2}  # bir marta uchraganlar — odatda ismlar/xatolar
    path.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
    get_vocab.cache_clear()
    return path


@lru_cache(maxsize=1)
def get_vocab() -> dict[str, int]:
    """Keshdagi lug'at; yo'q bo'lsa korpusdan quriladi (bir marta, bir necha soniya). Korpus bo'sh bo'lsa — {}."""
    path = vocab_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    counts = build_vocab()
    if counts:
        save_vocab(counts, path)
    return dict(counts)


def _variants(word: str):
    spots = [i for i, ch in enumerate(word) if ch in SWAP]
    if not spots or len(spots) > MAX_SWAPS:
        return
    for n in range(1, len(spots) + 1):
        for chosen in combinations(spots, n):
            chars = list(word)
            for i in chosen:
                chars[i] = SWAP[chars[i]]
            yield "".join(chars)


def _restore_case(original: str, fixed_lower: str) -> str:
    return "".join(f.upper() if o.isupper() else f for o, f in zip(original, fixed_lower))


def fix_word(word: str, vocab: dict[str, int]) -> str:
    """Bitta so'z uchun eng ehtimolli yozilish; tuzatish topilmasa — o'zi."""
    lower = word.lower()
    own = vocab.get(lower, 0)
    best, best_freq = None, 0
    for variant in _variants(lower):
        freq = vocab.get(variant, 0)
        if freq > best_freq:
            best, best_freq = variant, freq
    if best is None or best_freq < MIN_FREQ or (own and best_freq < own * DOMINANCE):
        return word
    return _restore_case(word, best)


def looks_uzbek(text: str, vocab: dict[str, int]) -> bool:
    words = [w.lower() for w in WORD_RE.findall(text) if len(w) >= 4]
    if not words or not vocab:
        return False
    known = sum(1 for w in words if vocab.get(w, 0) >= MIN_FREQ or fix_word(w, vocab) != w)
    return known / len(words) >= UZBEK_SHARE


def fix_uzbek_cyrillic(text: str, vocab: dict[str, int] | None = None) -> tuple[str, int]:
    """OCR matnidagi ў қ ғ ҳ ni tiklaydi. Qaytaradi: (matn, o'zgargan so'zlar soni). Matn o'zbekcha emas deb
    topilsa yoki lug'at bo'sh bo'lsa — o'zgarishsiz (0)."""
    vocab = get_vocab() if vocab is None else vocab
    if not vocab or not looks_uzbek(text, vocab):
        return text, 0
    changed = 0

    def repl(m: re.Match) -> str:
        nonlocal changed
        word = m.group(0)
        if len(word) < MIN_WORD_LEN:
            return word
        fixed = fix_word(word, vocab)
        changed += fixed != word
        return fixed

    return WORD_RE.sub(repl, text), changed
