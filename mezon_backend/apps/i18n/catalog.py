"""Tarjima kataloglari: matnlarni kod va shablonlardan ajratish, .po fayllarni yangilash, .mo ga kompilyatsiya.

Windows da GNU gettext (xgettext/msgfmt) yo'q, shuning uchun `makemessages` / `compilemessages` o'rniga shu modul
(`manage.py i18n_sync`) ishlatiladi; fayllar standart `.po` / `.mo` formatida — production da oddiy gettext asboblari
ham ishlaydi.

Manba til — oʻzbek (lotin): kod va shablonlardagi matnlarning o'zi msgid. Ajratiladigan joylar:
  * shablonlarda: {% trans "..." %}, {% translate '...' %}, {% blocktrans trimmed %}...{% endblocktrans %}
    (o'zgaruvchilar `{{ n }}` -> `%(n)s`);
  * brauzer JS ida (shablon ichida): gettext("..."), gettext('...'), gettext(`...`); interpolate(gettext("%(n)s ta"), {n: 3}, true);
  * Python da: _("..."), gettext(...), gettext_lazy(...), gettext_noop(...), pgettext emas.
  * frontend da (`../frontend/apps`, `../frontend/packages`, *.ts / *.tsx): t("..."), t('...'), t(`...`);
    i18next o'rinbosarlari `{{n}}` -> `%(n)s` (eksportda teskari: `i18n_export_json`).
Katalog: locale/<til>/LC_MESSAGES/django.po (til = to_locale: uz_Latn, uz_Cyrl, ru, kaa, en). uz_Cyrl matnlari
bo'sh qolsa, deterministik transliteratsiya bilan to'ldiriladi (`translit.lat_to_cyr`).
"""
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import polib
from django.conf import settings
from django.utils.translation import to_locale

from .translit import lat_to_cyr, lat_to_new_latn

SOURCE_LANG = "uz-latn"
PLACEHOLDER_RE = re.compile(r"%\(\w+\)s|%[sd]")
PROTECT_RE = re.compile(r"(%\(\w+\)s|%[sd]|<[^>]+>|&\w+;)")
PY_FUNCS = {"_", "gettext", "gettext_lazy", "gettext_noop", "ngettext"}

TRANS_RE = re.compile(r"""{%\s*trans(?:late)?\s+(?P<q>["'])(?P<s>(?:(?!(?P=q)).)*)(?P=q)""", re.S)
BLOCK_RE = re.compile(r"{%\s*blocktrans(?:late)?(?P<opts>[^%]*)%}(?P<body>.*?){%\s*endblocktrans(?:late)?\s*%}", re.S)
VAR_RE = re.compile(r"{{\s*(\w+)\s*}}")
# Frontend: t("...") / t('...') / t(`...`); oldida harf, nuqta yoki $ bo'lmasin (alert(, obj.t( emas)
TS_RE = re.compile(r"""(?<![\w.$])t\(\s*(?P<q>["'`])(?P<s>(?:\\.|(?!(?P=q)).)*)(?P=q)\s*[,)]""", re.S)
I18NEXT_VAR_RE = VAR_RE   # i18next o'rinbosari {{ n }} — Django shablonidagi bilan bir xil ko'rinish
FRONTEND_DIRS = ("apps", "packages")
FRONTEND_SKIP = {"node_modules", "dist", "build", ".expo"}
JS_RE = re.compile(r"""\bgettext\(\s*(?P<q>["'`])(?P<s>(?:\\.|(?!(?P=q)).)*)(?P=q)\s*\)""", re.S)


@dataclass
class Message:
    msgid: str
    places: list[str] = field(default_factory=list)


def locale_dir() -> Path:
    return Path(settings.LOCALE_PATHS[0])


def po_path(lang: str) -> Path:
    return locale_dir() / to_locale(lang) / "LC_MESSAGES" / "django.po"


def _unescape_js(s: str) -> str:
    return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s)


def _add(found: dict[str, Message], msgid: str, place: str) -> None:
    msgid = msgid.strip() if "\n" in msgid else msgid
    if msgid:
        found.setdefault(msgid, Message(msgid)).places.append(place)


def extract_template(path: Path, rel: str, found: dict[str, Message]) -> None:
    text = path.read_text(encoding="utf-8")
    line = lambda pos: text.count("\n", 0, pos) + 1
    for m in TRANS_RE.finditer(text):
        _add(found, m.group("s"), f"{rel}:{line(m.start())}")
    for m in BLOCK_RE.finditer(text):
        body = m.group("body")
        if "trimmed" in m.group("opts"):
            body = " ".join(part.strip() for part in body.splitlines() if part.strip())
        _add(found, VAR_RE.sub(lambda v: f"%({v.group(1)})s", body), f"{rel}:{line(m.start())}")
    for m in JS_RE.finditer(text):
        _add(found, _unescape_js(m.group("s")), f"{rel}:{line(m.start())}")


def extract_python(path: Path, rel: str, found: dict[str, Message]) -> None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
        arg = node.args[0]
        if func in PY_FUNCS and isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            _add(found, arg.value, f"{rel}:{node.lineno}")


def extract_frontend(path: Path, rel: str, found: dict[str, Message]) -> None:
    text = path.read_text(encoding="utf-8")
    for m in TS_RE.finditer(text):
        if m.group("q") == "`" and "${" in m.group("s"):
            continue   # shablon satri — dinamik kalit ajratilmaydi
        msgid = I18NEXT_VAR_RE.sub(lambda v: f"%({v.group(1)})s", _unescape_js(m.group("s")))
        _add(found, msgid, f"{rel}:{text.count(chr(10), 0, m.start()) + 1}")


def extract_messages(root: Path | None = None) -> dict[str, Message]:
    root = Path(root or settings.BASE_DIR)
    found: dict[str, Message] = {}
    for path in sorted((root / "apps").rglob("*")):
        rel = path.relative_to(root).as_posix()
        if "migrations" in path.parts or "tests" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix == ".html":
            extract_template(path, rel, found)
        elif path.suffix == ".py":
            extract_python(path, rel, found)
    frontend = root.parent / "frontend"
    for sub in FRONTEND_DIRS:
        for path in sorted((frontend / sub).rglob("*.ts*")):
            if path.suffix not in (".ts", ".tsx") or path.name.endswith((".d.ts", ".test.ts", ".test.tsx")):
                continue
            if FRONTEND_SKIP & set(path.parts):
                continue
            extract_frontend(path, path.relative_to(root.parent).as_posix(), found)
    return found


def transliterate_msgstr(msgid: str) -> str:
    """Placeholder va HTML teglarga tegmasdan lotin -> kirill."""
    return "".join(part if PROTECT_RE.fullmatch(part) else lat_to_cyr(part) for part in PROTECT_RE.split(msgid))


def transliterate_new_latn_msgstr(msgid: str) -> str:
    """Placeholder va HTML teglarga tegmasdan eski lotin (1995) -> 2026 yangi lotin."""
    return "".join(part if PROTECT_RE.fullmatch(part) else lat_to_new_latn(part) for part in PROTECT_RE.split(msgid))


def _new_po(lang: str) -> polib.POFile:
    po = polib.POFile()
    po.metadata = {
        "Project-Id-Version": "MEZON AI", "Language": to_locale(lang), "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8", "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": "nplurals=2; plural=(n != 1);",
    }
    return po


def load_po(lang: str) -> polib.POFile:
    path = po_path(lang)
    return polib.pofile(str(path)) if path.exists() else _new_po(lang)


def sync(root: Path | None = None) -> dict[str, dict]:
    """Barcha tillar uchun .po ni yangilaydi (yangi matnlar qo'shiladi, yo'qolganlari obsolete) va .mo ni yozadi.
    Qaytaradi: {til: {total, translated, missing: [msgid], placeholder_errors: [msgid]}}."""
    found = extract_messages(root)
    report: dict[str, dict] = {}
    for lang, _ in settings.LANGUAGES:
        po = load_po(lang)
        existing = {e.msgid: e for e in po}
        for msgid, msg in found.items():
            entry = existing.get(msgid)
            if entry is None:
                entry = polib.POEntry(msgid=msgid)
                po.append(entry)
            entry.obsolete = False
            entry.occurrences = [tuple(p.rsplit(":", 1)) for p in dict.fromkeys(msg.places)][:5]
            if lang == "uz-cyrl" and not entry.msgstr:
                entry.msgstr = transliterate_msgstr(msgid)
            elif lang == "uz-latn-2026" and not entry.msgstr:
                entry.msgstr = transliterate_new_latn_msgstr(msgid)
        for msgid, entry in existing.items():
            if msgid not in found:
                entry.obsolete = True
        po.sort(key=lambda e: (e.obsolete, e.msgid))
        path = po_path(lang)
        path.parent.mkdir(parents=True, exist_ok=True)
        po.save(str(path))
        po.save_as_mofile(str(path.with_suffix(".mo")))
        live = [e for e in po if not e.obsolete]
        source = lang == SOURCE_LANG   # manba til: msgid ning o'zi matn, msgstr kerak emas
        report[lang] = {
            "total": len(live),
            "translated": len(live) if source else sum(1 for e in live if e.msgstr),
            "missing": [] if source else [e.msgid for e in live if not e.msgstr],
            "placeholder_errors": [e.msgid for e in live if e.msgstr and
                                   sorted(PLACEHOLDER_RE.findall(e.msgid)) != sorted(PLACEHOLDER_RE.findall(e.msgstr))],
        }
    return report
