"""Shaxsiy ma'lumotlarni niqoblash (TZ §5.3): matn LLM ga yuborilishidan oldin.

1. Raqamli identifikatorlar (regex): JSHSHIR (14 raqam), telefon (+998 …), pasport (AA 1234567), karta raqami.
2. Ism-familiyalar (qoidalar asosida, API siz):
   - to'liq F.I.Sh. (lotin/kirill: "Qodirova Malika Anvarovna", "Эргашев Шуҳрат Комилович") va initsialli shakllar
     ("M.A. Qodirova", "Н.Ш. Юсупов", "Кодировой М.А.") topiladi;
   - familiya o'zagi (Qodirov-, Кодиров-) ajratiladi va uning barcha shakllari (Qodirovaning, Кодировой) niqoblanadi;
     lotin va kirill o'zaklari bitta shaxsga bog'lanadi (transliteratsiya bilan solishtiriladi);
   - faqat ism bilan tilga olinsa ("Jasur ismli shaxs"): ism bitta shaxsga tegishli bo'lsa — o'sha shaxs tokeni,
     aks holda <ISM>.
Bir xil shaxs butun ish bo'yicha bir xil tokenga almashadi (<SHAXS_1>), asl qiymatlar faqat `PiiVault` da (xotirada).
Cheklov: familiyasiz va "ismli" so'zisiz tilga olingan ismlar (masalan, "Otabek") niqoblanmasligi mumkin.
"""
import re
from dataclasses import dataclass, field

PATTERNS = [
    ("JSHSHIR", re.compile(r"(?<!\d)\d{14}(?!\d)")),
    ("TEL", re.compile(r"\+998[\s-]?\(?\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")),
    ("PASPORT", re.compile(r"\b[A-Z]{2}\s?\d{7}\b")),
    # OCR "****" ni ba'zan "***" deb o'qiydi, raqam qator oxirida bo'linishi ham mumkin
    ("KARTA", re.compile(r"\b\d{4}[\s*]{1,3}(?:\*{3,4}|\d{4})[\s*]{1,3}(?:\*{3,4}|\d{4})[\s*]{1,3}\d{4}\b")),
]

L = "A-Za-zʻʼ'’`"                   # lotin harflari (o'zbekcha apostroflar bilan)
C = "А-Яа-яЁёЎўҚқҒғҲҳ"             # kirill harflari
UP = "A-ZА-ЯЁЎҚҒҲ"
W = rf"[{UP}][{L}{C}]+"             # bosh harf bilan boshlanuvchi so'z
# Familiya oxiri: -ov/-ev/-in + faqat kelishik qo'shimchalari ("Tergovchi" kabi so'zlar familiya emas).
SURNAME_TAIL = (r"(?:ov|ev|in|ов|ев|ин)"
                r"(?:a|aning|ani|aga|ada|adan|ning|ni|ga|da|dan|"
                r"а|ой|ым|у|е|ы|ого|ому|нинг|ни|га|да|дан|анинг|ани|ага|ада|адан)?")
PATRONYMIC_TAIL = r"(?:ovich|ovna|yevich|yevna|evich|evna|ович|овна|евич|евна|овичу|овной|овны|овичем|o['ʻ’`]?g['ʻ’`]?li|qizi)"
INITIAL = rf"[{UP}][a-zа-яʻ]?\."

FULL_NAME = re.compile(rf"\b({W}{SURNAME_TAIL})\s+({W})\s+({W}{PATRONYMIC_TAIL}[{L}{C}]*)\b")  # Familiya Ism Otasining(ni)
SURNAME_NAME = re.compile(rf"\b({W}{SURNAME_TAIL}) ({W})\b")                                   # Hasanova Dilnoza (bitta qatorda)
INITIALS_BEFORE = re.compile(rf"(?<![{L}{C}])((?:{INITIAL}\s?){{1,2}})\s?({W}{SURNAME_TAIL})\b")  # M.A. Qodirova
INITIALS_AFTER = re.compile(rf"\b({W}{SURNAME_TAIL})\s((?:{INITIAL}\s?){{1,2}})")              # Кодировой М.А.
NAMED_AS = re.compile(rf"\b({W})\s+(?:ismli|исмли)\b")                                            # Jasur ismli

CYR2LAT = str.maketrans({"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "j", "з": "z",
                         "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
                         "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "s", "ч": "ch", "ш": "sh", "щ": "sh",
                         "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "k", "ғ": "g",
                         "ҳ": "h"})


def match_key(word: str) -> str:
    """Lotin/kirill yozuvidagi so'zni solishtirish uchun bitta shaklga keltiradi (Qodirov ~ Кодиров -> kodirov)."""
    w = word.lower().translate(CYR2LAT)
    w = re.sub(r"[ʻʼ'’`]", "", w).replace("q", "k").replace("x", "h").replace("ye", "e")
    return w


def surname_stem(word: str) -> str | None:
    """'Qodirovaning' -> 'kodirov', 'Кодировой' -> 'kodirov', 'Yusupov' -> 'yusupov'."""
    m = re.match(r"(.{3,}?(?:ov|ev|in))", match_key(word))
    return m.group(1) if m else None


@dataclass
class Person:
    token: str
    stems: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)  # ism va otasining ismi (match_key shaklida)
    originals: list[str] = field(default_factory=list)


@dataclass
class PiiVault:
    to_token: dict[str, str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    persons: list[Person] = field(default_factory=list)

    def token(self, kind: str, value: str) -> str:
        key = re.sub(r"[\s()-]", "", value)
        if key not in self.to_token:
            self.counters[kind] = self.counters.get(kind, 0) + 1
            self.to_token[key] = f"<{kind}_{self.counters[kind]}>"
        return self.to_token[key]

    # ---------------------------------------------------------------- shaxslar

    def _with_stem(self, stem: str) -> list[Person]:
        return [p for p in self.persons if stem in p.stems]

    def _person(self, stem: str, name: str | None = None) -> Person:
        """Familiya o'zagi (+ ism) bo'yicha shaxs. Bir familiyali turli shaxslar (Karimov Jasur va Karimova Malika —
        er-xotin, ota-qiz) ism bilan ajratiladi; ism berilmasa — shu o'zakdagi birinchi shaxs."""
        same = self._with_stem(stem)
        if same and name is None:
            return same[0]
        for p in same:
            if name in p.names:
                return p
        for p in same:
            if not p.names:   # hali ismi yo'q shaxs (faqat initsiallar bilan tanilgan) — shu ismni oladi
                return p
        self.counters["SHAXS"] = self.counters.get("SHAXS", 0) + 1
        p = Person(token=f"<SHAXS_{self.counters['SHAXS']}>", stems={stem})
        self.persons.append(p)
        return p

    def _find(self, stem: str, name: str) -> Person | None:
        """Yangi shaxs yaratmasdan: shu familiya o'zagi va ismli shaxs."""
        return next((p for p in self._with_stem(stem) if name in p.names), None)

    def learn_names(self, texts: list[str]) -> None:
        """Butun ish matnidan shaxslarni yig'adi (niqoblashdan oldin, barcha sahifalar bo'yicha)."""
        for text in texts:
            for m in FULL_NAME.finditer(text):
                stem = surname_stem(m.group(1))
                if stem:
                    p = self._person(stem, match_key(m.group(2)))
                    patronymic = re.sub(rf"{PATRONYMIC_TAIL}[{L}{C}]*$", "", m.group(3))
                    p.names.update({match_key(m.group(2)), match_key(patronymic)})
                    p.originals.append(m.group(0))
            for rx, group in ((INITIALS_BEFORE, 2), (INITIALS_AFTER, 1)):
                for m in rx.finditer(text):
                    stem = surname_stem(m.group(group))
                    if stem:
                        self._person(stem).originals.append(m.group(0))
        # "Hasanova Dilnoza" — ism faqat familiyasi allaqachon tanilgan shaxsga yoziladi (tasodifiy so'zlar emas).
        known = {s for p in self.persons for s in p.stems}
        for text in texts:
            for m in SURNAME_NAME.finditer(text):
                if "." in text[max(0, m.start() - 4):m.start()]:
                    continue  # "N.Sh. Yusupov Sergeli tumani" — initsialdan keyin keladigan so'z ism emas
                stem = surname_stem(m.group(1))
                if stem in known and not re.search(PATRONYMIC_TAIL, m.group(2)):
                    same = self._with_stem(stem)
                    name = match_key(m.group(2))
                    # Yangi shaxs yaratilmaydi: ismi hali yo'q shaxsga (yoki yagona shaxsga) yoziladi
                    target = next((p for p in same if name in p.names), None) or next(
                        (p for p in same if not p.names), None) or (same[0] if len(same) == 1 else None)
                    if target is not None:
                        target.names.add(name)

    def _mask_names(self, text: str) -> str:
        if not self.persons:
            return text
        name_owner: dict[str, list[Person]] = {}
        for p in self.persons:
            for n in p.names:
                if len(n) >= 3:
                    name_owner.setdefault(n, []).append(p)

        # Initsiallar shaxs tokeni bilan birga yo'qoladi: "M.A. Qodirova" -> "<SHAXS_1>".
        def by_surname(word: str) -> str | None:
            """Familiya -> token. Bir familiyali bir nechta shaxs bo'lsa — barchasining tokeni ("<SHAXS_1>/<SHAXS_2>"):
            noaniq holda bitta shaxsga tegishli qilib qo'ymaymiz."""
            stem = surname_stem(word)
            tokens = [p.token for p in self._with_stem(stem)] if stem else []
            return "/".join(tokens) or None

        def initials_before(m):
            return by_surname(m.group(2)) or m.group(0)

        def initials_after(m):
            token = by_surname(m.group(1))
            return token + " " if token else m.group(0)

        # Bir familiyali shaxslar: "Karimov Jasur Anvarovich" / "Karimova Malika" — ism bo'yicha aniq shaxsga
        def by_full_name(m):
            stem = surname_stem(m.group(1))
            p = self._find(stem, match_key(m.group(2))) if stem and len(self._with_stem(stem)) > 1 else None
            return p.token if p else m.group(0)

        text = FULL_NAME.sub(by_full_name, text)
        text = SURNAME_NAME.sub(by_full_name, text)
        text = INITIALS_BEFORE.sub(initials_before, text)
        text = INITIALS_AFTER.sub(initials_after, text)

        def word(m):
            w = m.group(0)
            token = by_surname(w)
            if token:
                return token
            key = match_key(w)
            for n, owners in name_owner.items():
                # ism yoki otasining ismi (qo'shimchalar bilan: Malikaning, Анваровной)
                if key == n or (key.startswith(n) and len(n) >= 4):
                    return owners[0].token if len({o.token for o in owners}) == 1 else "<ISM>"
            return w

        text = re.sub(rf"\b{W}\b", word, text)
        text = NAMED_AS.sub(lambda m: m.group(0) if m.group(1).startswith("<") else "<ISM> ismli", text)
        # "<SHAXS_7> <SHAXS_7> <SHAXS_7>" (familiya, ism, otasining ismi) -> "<SHAXS_7>"
        return re.sub(r"(<SHAXS_\d+>)(?:[ \t]+\1)+", r"\1", text)

    # ---------------------------------------------------------------- umumiy

    def mask(self, text: str) -> str:
        for kind, rx in PATTERNS:
            text = rx.sub(lambda m, k=kind: self.token(k, m.group(0)), text)
        return self._mask_names(text)

    def unmask(self, text: str) -> str:
        back = {v: k for k, v in self.to_token.items()}
        back.update({p.token: (p.originals[0] if p.originals else p.token) for p in self.persons})
        # Model ba'zan tokenni burchak qavssiz yozadi ("guvoh SHAXS_7") — u ham asl qiymatga qaytariladi.
        return re.sub(r"<?\b([A-Z]+_\d+)\b>?", lambda m: back.get(f"<{m.group(1)}>", m.group(0)), text)
