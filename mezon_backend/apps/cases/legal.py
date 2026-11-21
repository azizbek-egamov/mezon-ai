"""Topilmalarni (ziddiyat, protsessual muammo) lex.uz moddalari bilan huquqiy asoslash (TZ §4.2–4.3).

1. LLM barcha topilmalar uchun bir chaqiruvda huquqiy qidiruv so'rovlarini tuzadi.
2. Har bir topilma uchun lex.uz korpusidan moddalar topiladi (GPU/Qdrant — ketma-ket).
3. LLM har bir topilmani FAQAT shu manbalar asosida baholaydi (parallel): me'yor «aynan» iqtibos bilan [M#],
   topilmadagi hisob-kitob qonunga zid bo'lsa — tuzatadi (masalan, ushlab turish muddati).
4. `verify_answer` har bir bahoni tekshiradi: [M#] mavjudmi, «iqtibos» manbada so'zma-so'z bormi; `verify_legal` —
   tilga olingan moddalar bazada bor va topilma sanasida kuchdami, iqtibos olingan qismdagi istisnolar tushmaganmi.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

from apps.rag.answer import CITE_RE, Source, verify_answer
from apps.rag.llm import get_llm, task_model
from apps.rag.locks import SEARCH_LOCK
from apps.rag.search import search
from apps.rag.verifier import verify_legal

from .analysis import Finding
from .case_types import (CASE_TYPES, CaseType, adapt_assess_system, adapt_query_system, get_case_type,
                         scope_of)
from .extract import Fact

logger = logging.getLogger(__name__)

SOURCES_PER_FINDING = 6
# Ish turi bo'yicha huquqiy qidiruv doirasi (document_ids YOKI doc_types) — apps/cases/case_types.py. Jinoyat ishida boshqa
# sohalarning protsessual kodekslari (Ma'muriy sud, Iqtisodiy protsessual) chalg'itadi — case_01 sinovida shunday bo'lgan.
CASE_SCOPES = {code: t.scope for code, t in CASE_TYPES.items()}

QUERY_SYSTEM = """Sen Oʻzbekiston qonunchiligini biladigan advokatsan. Senga jinoyat ishi boʻyicha topilmalar roʻyxati beriladi.
Har bir topilmani huquqiy baholash uchun lex.uz dan qaysi normalar kerak boʻlsa, ularni topish uchun 2-3 ta qidiruv soʻrovi tuz:
RASMIY HUQUQIY ATAMALARDA (masalan: "ushlab turish muddati", "dalillarga baho berish", "ekspertiza tayinlash toʻgʻrisidagi
qaror bilan tanishtirish", "tanib olish uchun koʻrsatish tartibi", "aybsizlik prezumpsiyasi shubhalar ayblanuvchi foydasiga").
Asosan Jinoyat-protsessual kodeksi, Jinoyat kodeksi, Konstitutsiya va Oliy sud Plenumi qarorlari. Modda raqamini oʻylab topma.
Faqat JSON."""

QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"index": {"type": "integer"}, "queries": {"type": "array", "items": {"type": "string"}}},
                "required": ["index", "queries"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

ASSESS_SYSTEM = """Sen jinoyat ishlari boʻyicha tajribali himoyachi-advokatsan. Senga ish boʻyicha bir nechta topilma beriladi;
har bir <topilma index="..."> ichida faktlar va shu topilma uchun lex.uz dan olingan qonun manbalari (<manba id="M..">) bor.
Har bir topilmani FAQAT oʻzining manbalari asosida huquqiy baholа.
Qoidalar:
1. Har bir huquqiy fikrdan keyin manbani koʻrsat: [M3]. Qonun meʼyorini «...» ichida manbadan AYNAN koʻchir va darhol [M#] qoʻy.
   Boshqa topilmaning manbasiga ishora qilma. verdict qonun_buzilishi yoki buzilish_ehtimoli boʻlsa, assessment da buzilgan
   meʼyor KAMIDA BITTA «aynan iqtibos» [M#] bilan keltirilishi SHART — iqtibossiz baho rad etiladi.
2. Topilmadagi muddat, soat yoki boshqa hisob qonundagi meʼyorga mos kelmasa — qonundagisini koʻrsatib QAYTA HISOBLA,
   corrections ga yoz (masalan: "topilmada 72 soat deyilgan, qonunda 48 soat") va correction_needed=true qoʻy;
   tuzatish kerak boʻlmasa correction_needed=false, corrections — boʻsh satr.
3. Manbalarda tegishli meʼyor boʻlmasa — buni ochiq yoz, taxmin qilma, modda raqamini oʻylab topma.
4. verdict: qonun_buzilishi (meʼyor aniq buzilgan) | buzilish_ehtimoli (qoʻshimcha tekshiruv kerak) |
   huquqiy_ahamiyatli (buzilish emas, lekin dalillarga baho berishda muhim) | asossiz (topilma qonun nuqtai nazaridan asossiz).
5. assessment — 2-4 gap, oʻzbek (lotin) tilida; defense_action — himoyachi nima talab qilishi kerak (1 gap).
6. Manbada [Voqea sanasidagi tahrir] va [Hozirgi tahrir] berilgan boʻlsa, voqea sanasidagisini qoʻlla; keyingi oʻzgarish ahvolni yengillashtirsa (jazo yumshatilgan, qilmish jinoyat emas deb topilgan), buni alohida koʻrsat — bunday qonun orqaga qaytish kuchiga ega boʻlishi mumkin.
Har bir topilma uchun index bilan bitta baho qaytar. Faqat JSON."""

ASSESS_ITEM = {
    "type": "object",
    "properties": {
        "index": {"type": "integer"},
        "verdict": {"type": "string", "enum": ["qonun_buzilishi", "buzilish_ehtimoli", "huquqiy_ahamiyatli", "asossiz"]},
        "assessment": {"type": "string"},
        "correction_needed": {"type": "boolean"},
        "corrections": {"type": "string"},
        "defense_action": {"type": "string"},
    },
    "required": ["index", "verdict", "assessment", "correction_needed", "corrections", "defense_action"],
    "additionalProperties": False,
}
ASSESS_SCHEMA = {
    "type": "object",
    "properties": {"assessments": {"type": "array", "items": ASSESS_ITEM}},
    "required": ["assessments"],
    "additionalProperties": False,
}

IMPORTANCE_RANK = {"low": 0, "medium": 1, "high": 2}
# Bu xulosalar qonun buzilganini da'vo qiladi — kamida bitta tekshirilgan qonun iqtibosi shart.
VIOLATION_VERDICTS = {"qonun_buzilishi", "buzilish_ehtimoli"}


@dataclass
class LegalAssessment:
    queries: list[str]
    sources: list[dict]
    verdict: str = ""
    assessment: str = ""
    correction_needed: bool = False
    corrections: str = ""
    defense_action: str = ""
    verification: dict = field(default_factory=dict)
    error: str = ""
    skipped: bool = False  # muhimligi past — asoslanmadi (xarajat tejash)
    model: str = ""         # qaysi model baholagan
    retried: bool = False   # birinchi baho tekshiruvdan o'tmagani uchun kuchliroq model bilan qayta baholangan


def finding_date(f: Finding, facts_by_id: dict[str, Fact]) -> date | None:
    """Topilma bo'yicha qo'llanadigan qonun sanasi: uning faktlaridagi eng kech sana (baholanayotgan harakat kuni).
    Protsessual normalar harakat sodir etilgan kundagi, moddiy normalar — jinoyat kunidagi tahrirda qo'llanadi;
    bu yaqinlashish — ikkalasi ham ishning vaqt oralig'ida."""
    days = []
    for fid in f.fact_ids:
        fact = facts_by_id.get(fid)
        try:
            days.append(date.fromisoformat((fact.date or "")[:10]))
        except (AttributeError, ValueError):  # fakt topilmadi yoki sanasi yo'q/noto'liq
            continue
    return max(days) if days else None


def _finding_brief(f: Finding, facts_by_id: dict[str, Fact], with_facts: bool = True) -> str:
    head = f"[{f.kind}] {f.topic}\n{f.explanation}"
    if not with_facts:
        return head
    lines = [f"  {fid} ({facts_by_id[fid].verified_page}-varaq, {facts_by_id[fid].source}): {facts_by_id[fid].summary} "
             f"— «{facts_by_id[fid].quote}»" for fid in f.fact_ids if fid in facts_by_id]
    return head + "\nFaktlar:\n" + "\n".join(lines)


def plan_queries(findings: list[Finding], facts_by_id: dict[str, Fact], ct: CaseType | None = None) -> dict[int, list[str]]:
    listing = "\n\n".join(f"#{i}: {_finding_brief(f, facts_by_id, with_facts=False)}" for i, f in enumerate(findings))
    data = get_llm().chat_json(adapt_query_system(QUERY_SYSTEM, ct or get_case_type(None)), "TOPILMALAR:\n" + listing, schema=QUERY_SCHEMA, effort="low",
                               max_tokens=8000, model=task_model("legal"))
    out: dict[int, list[str]] = {}
    for item in data.get("items", []):
        qs = [q.strip() for q in item.get("queries", []) if isinstance(q, str) and q.strip()][:3]
        if qs and 0 <= item.get("index", -1) < len(findings):
            out[item["index"]] = qs
    return out


def _assess_batch(batch: list[int], findings: list[Finding], sources: dict[int, list[Source]],
                  facts_by_id: dict[str, Fact], effort: str, model: str | None,
                  ct: CaseType | None = None) -> dict[int, dict]:
    blocks = []
    for i in batch:
        rendered = "\n\n".join(s.render() for s in sources[i])
        blocks.append(f'<topilma index="{i}">\n<manbalar>\n{rendered}\n</manbalar>\n\nTOPILMA:\n'
                      f"{_finding_brief(findings[i], facts_by_id)}\n</topilma>")
    data = get_llm().chat_json(adapt_assess_system(ASSESS_SYSTEM, ct or get_case_type(None)), "\n\n".join(blocks), schema=ASSESS_SCHEMA, effort=effort,
                               max_tokens=12000, model=model)
    return {a["index"]: a for a in data.get("assessments", []) if a.get("index") in batch}


def _keyed_sources(batch: list[int], hits_by_finding: dict[int, list]) -> dict[int, list[Source]]:
    """Guruh ichida manba kalitlari takrorlanmaydi (M1..Mn): model boshqa topilmaning manbasiga ishora qilsa,
    iqtibos aynan o'sha manbadan tekshiriladi va manba bahoga qo'shiladi."""
    keyed, counter = {}, 0
    for i in batch:
        keyed[i] = [Source(key=f"M{counter + n}", hit=h) for n, h in enumerate(hits_by_finding[i], 1)]
        counter += len(hits_by_finding[i])
    return keyed


def ground_findings(findings: list[Finding], facts: list[Fact], effort: str = "low", batch_size: int = 4, category: str = "criminal",
                    min_importance: str = "low", workers: int = 3,
                    retry_min_importance: str = "high") -> list[LegalAssessment]:
    """Har bir topilma uchun LegalAssessment (findings tartibida). min_importance dan past topilmalar o'tkazib
    yuboriladi (skipped=True). batch_size ta topilma bitta LLM chaqiruvida baholanadi — xarajat kamayadi.
    Kaskad: avval arzon model (LLM_MODEL_LEGAL); tekshiruvdan o'tmagan yoki xato bergan baholar kuchliroq model
    (LLM_MODEL_LEGAL_RETRY) bilan qayta baholanadi."""
    ct = get_case_type(category)
    facts_by_id = {f.id: f for f in facts}
    active = [i for i, f in enumerate(findings)
              if IMPORTANCE_RANK.get(f.importance, 0) >= IMPORTANCE_RANK[min_importance]]
    results = [LegalAssessment(queries=[], sources=[], skipped=True) for _ in findings]
    if not active:
        return results
    queries = plan_queries([findings[i] for i in active], facts_by_id, ct)

    dates = {i: finding_date(findings[i], facts_by_id) for i in active}
    # Qidiruv — ketma-ket (bitta GPU va ichki Qdrant).
    hits_by_finding: dict[int, list] = {}
    with SEARCH_LOCK:  # chat so'rovlari bilan umumiy GPU/Qdrant
        for n, i in enumerate(active):
            qs = queries.get(n, [findings[i].topic])
            hits_by_finding[i] = search(f"{findings[i].topic}. {findings[i].explanation[:300]}",
                                        limit=SOURCES_PER_FINDING, expansions=qs,
                                        on_date=dates[i], **scope_of(category))
            results[i] = LegalAssessment(queries=qs, sources=[])

    def run(batch: list[int], model: str | None, retried: bool) -> None:
        sources = _keyed_sources(batch, hits_by_finding)
        try:
            assessed = _assess_batch(batch, findings, sources, facts_by_id, effort, model, ct)
        except Exception as e:
            logger.error("Topilmalar %s ni baholab bo'lmadi: %s", batch, e)
            for i in batch:   # hisobotga umumiy matn: xato tafsiloti (URL, kalit) faqat logda
                results[i].error = "Huquqiy bahoni olib boʻlmadi (texnik xato)"
            return
        for i in batch:
            data = assessed.get(i)
            result = results[i]
            result.model, result.retried = model or "", retried
            # Partiyadagi boshqa topilmaning manbasidan aynan iqtibos ham haqiqiy qonun matni — rad etmaymiz
            # (avval bu xato hisoblanib, qimmat qayta baholashga sabab bo'lardi), manba ro'yxatiga qo'shamiz.
            cited = set(CITE_RE.findall(f"{data['assessment']}\n{data['corrections']}")) if data else set()
            batch_sources = sources[i] + [s for j in batch if j != i for s in sources[j] if s.key in cited]
            result.sources = [{"key": s.key, "doc_title": s.hit.doc_title, "label": s.hit.label,
                               "lex_url": s.hit.lex_url} for s in batch_sources]
            if data is None:
                result.error = "Model bu topilma uchun baho qaytarmadi"
                continue
            result.error = ""
            result.verdict, result.assessment = data["verdict"], data["assessment"]
            result.correction_needed = bool(data.get("correction_needed"))
            result.corrections, result.defense_action = data["corrections"], data["defense_action"]
            text = f"{result.assessment}\n{result.corrections}"
            report = verify_answer(text, batch_sources)
            report.issues += verify_legal(text, batch_sources, dates[i])  # bazada, sanada kuchda, istisnolar
            issues = [x.__dict__ for x in report.issues]
            if report.quotes_checked == 0:
                # Buzilish da'vosi qonun matnisiz — tekshiradigan narsa yo'q, shuning uchun o'tmagan hisoblanadi.
                severity = "error" if result.verdict in VIOLATION_VERDICTS else "warning"
                issues.append({"severity": severity, "kind": "qonun_iqtibosi_yoq",
                               "detail": "Bahoda qonun meʼyoridan «aynan iqtibos» [M#] yoʻq"})
            result.verification = {"ok": not any(x["severity"] == "error" for x in issues),
                                   "citations": report.citations, "quotes_checked": report.quotes_checked,
                                   "issues": issues}

    def run_all(indices: list[int], model: str | None, retried: bool) -> None:
        batches = [indices[k:k + batch_size] for k in range(0, len(indices), batch_size)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(lambda b: run(b, model, retried), batches))

    first_model, retry_model = task_model("legal"), task_model("legal_retry")
    run_all(active, first_model, retried=False)
    # Qimmat model bilan qayta baholash faqat retry_min_importance va undan yuqori topilmalar uchun.
    failed = [i for i in active if (results[i].error or not results[i].verification.get("ok"))
              and IMPORTANCE_RANK.get(findings[i].importance, 0) >= IMPORTANCE_RANK[retry_min_importance]]
    if failed and retry_model and retry_model != first_model:
        logger.warning("Huquqiy asoslash: %s ta baho tekshiruvdan o'tmadi — %s bilan qayta baholanadi",
                       len(failed), retry_model)
        run_all(failed, retry_model, retried=True)
    return results
