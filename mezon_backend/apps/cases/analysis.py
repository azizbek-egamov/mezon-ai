"""Faktlardan xronologiya, ichki ziddiyatlar va protsessual muammolar (TZ §4.1 p.4, Contradiction Matrix).

LLM ga faqat iqtibosi tekshirilgan faktlar beriladi (id, varaq, sana/vaqt, manba, mazmun). U ziddiyatlarni
fakt id lari bilan qaytaradi; kod id larni tekshiradi, varaq raqamlarini faktlardan oladi — model varaq yoki
fakt o'ylab topa olmaydi.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from apps.rag.llm import get_llm, task_model

from .case_types import (adapt_analysis_common, adapt_contradiction_task, get_case_type,
                         procedural_task)
from .extract import Fact

COMMON = """Sen jinoyat ishlari boʻyicha tajribali himoyachi-advokatsan. Senga ish hujjatlaridan ajratilgan faktlar roʻyxati
beriladi (har birida id, varaq, sana/vaqt, manba — kim aytgani yoki qaysi hujjat, mazmun).
Qoidalar: faqat berilgan faktlarga tayan, yangi fakt qoʻshma; importance: high | medium | low. Qonun moddalarini raqam
bilan yozma — huquqiy baho keyingi bosqichda lex.uz manbalari bilan beriladi. Javob oʻzbek (lotin) tilida.
IXCHAM yoz: koʻpi bilan 12 ta eng muhim band (muhimlik tartibida), har bir explanation — koʻpi bilan 3 gap. Faqat JSON."""

TASKS = {
    "contradiction": ("contradictions", 2, """
Vazifa:
1. contradictions — faktlar orasidagi ICHKI ZIDDIYATLAR: turli shaxslar yoki hujjatlar bir xil holat (vaqt, joy, summa, sana,
   rang, raqam, ekspertiza xulosasi va hokazo) haqida mos kelmaydigan maʼlumot bergan, yoki yakuniy hujjat (masalan, ayblov
   xulosasi) ishdagi dalillarni notoʻgʻri bayon qilgan. Har bir ziddiyatga uni tashkil etuvchi BARCHA fakt id larini qoʻy
   (kamida ikkita). Protsessual masalalarni (muddatlar, qarorlar bilan tanishtirish, tanib olish/tintuv tartibi,
   iltimosnomalar, qamoq asoslari) YOZMA — ular alohida tahlil qilinadi.
2. summary — ish holati boʻyicha himoyachi uchun 3-5 gaplik xulosa."""),
    "procedural": ("procedural_issues", 1, """
Vazifa: procedural_issues — protsessual muddatlar va tartib buzilishi ehtimoli: ushlab turish va qamoqqa olish muddatlari
(soat bilan hisobla), shaxsni qarorlar bilan kech tanishtirish, tanib olish/tintuv tartibi, himoya iltimosnomalarining
asossiz rad etilishi, ayblovni rad etuvchi dalillarning eʼtiborsiz qoldirilishi va hokazo. Hisob-kitobni explanation da
koʻrsat. Har bir band kamida bitta fakt id siga tayansin. Koʻrsatuvlar va hujjatlar orasidagi faktik ziddiyatlarni
(vaqt, summa, sana, rang, ayblov xulosasida ekspertiza yoki boshqa dalilning notoʻgʻri bayoni) YOZMA — ular alohida
tahlil qilinadi; bu yerda faqat tartib va muddat masalalari. summary — boʻsh satr."""),
}

ITEM = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "fact_ids": {"type": "array", "items": {"type": "string"}},
        "explanation": {"type": "string"},
        "importance": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["topic", "fact_ids", "explanation", "importance"],
    "additionalProperties": False,
}


def _schema(key: str) -> dict:
    return {
        "type": "object",
        "properties": {key: {"type": "array", "items": ITEM}, "summary": {"type": "string"}},
        "required": [key, "summary"],
        "additionalProperties": False,
    }


@dataclass
class Finding:
    kind: str  # contradiction | procedural
    topic: str
    fact_ids: list[str]
    pages: list[int]
    explanation: str
    importance: str
    dropped_ids: list[str] = field(default_factory=list)  # model ko'rsatgan, lekin mavjud bo'lmagan id lar


def timeline(facts: list[Fact]) -> list[Fact]:
    dated = [f for f in facts if f.verified and f.date]
    return sorted(dated, key=lambda f: (f.date, f.time or "99:99", f.verified_page or f.page))


def _render_facts(facts: list[Fact]) -> str:
    return "\n".join(
        f"{f.id} | {f.verified_page}-varaq | {f.date} {f.time} | {f.source} | {f.summary}" for f in facts
    )


def find_issues(facts: list[Fact], effort: str = "medium", model: str | None = None,
                case_type: str = "criminal") -> tuple[list[Finding], str]:
    """Ziddiyatlar va protsessual muammolar ikki parallel chaqiruvda: katta ishda bitta javob chegaraga
    (max_tokens) sig'may kesilardi (case_01 skaner nusxasi, 141 fakt)."""
    verified = [f for f in facts if f.verified]
    by_id = {f.id: f for f in verified}
    listing = "FAKTLAR:\n" + _render_facts(verified)
    model = model or task_model("analysis")
    ct = get_case_type(case_type)   # ish turi (12-bosqich): rol va protsessual vazifa shunga moslanadi

    def run(kind: str) -> dict:
        key, _, task = TASKS[kind]
        task = adapt_contradiction_task(task, ct) if kind == "contradiction" else procedural_task(task, ct)
        return get_llm().chat_json(adapt_analysis_common(COMMON, ct) + task, listing, schema=_schema(key), effort=effort, max_tokens=16000,
                                   model=model)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(zip(TASKS, pool.map(run, TASKS)))

    findings: list[Finding] = []
    for kind, data in results.items():
        key, min_facts, _ = TASKS[kind]
        for item in data.get(key, []):
            ids = list(dict.fromkeys(item.get("fact_ids", [])))
            valid = [i for i in ids if i in by_id]
            if len(valid) < min_facts:
                continue
            findings.append(Finding(
                kind=kind, topic=item["topic"], fact_ids=valid,
                pages=sorted({by_id[i].verified_page for i in valid}),
                explanation=item["explanation"], importance=item["importance"],
                dropped_ids=[i for i in ids if i not in by_id],
            ))
    return findings, results["contradiction"].get("summary", "")
