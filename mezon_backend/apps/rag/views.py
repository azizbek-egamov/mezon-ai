"""Chat sahifasi va iqtibosli javob API si (Server-Sent Events stream).

POST /api/ask  {"question": "...", "lang": "uz-Latn", "effort": "medium"}
Javob — text/event-stream, hodisalar tartibi:
  aspects       [{topic, queries}]                  (savol qaysi huquqiy yo'nalishlarga ajratilgani)
  sources       [{key, topic, doc_title, label, lex_url, edition, exact}]
  delta         {"text": "..."}                     (ko'p marta)
  verification  {ok, citations, quotes_checked, issues: [{severity, kind, detail}]}
  done          {timings: {...}, usage: {...}}
  error         {"message": "..."}                  (xato bo'lsa, oqim shu bilan tugaydi)
"""
import json
import logging
import re
import time
from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.decorators import api_login_required
from apps.billing import quota
from apps.i18n.codes import to_django_code
from apps.i18n.translit import lat_to_new_latn
from apps.lex_corpus.models import corpus_lang

from .answer import LANG_NAMES, build_prompt, build_sources, verify_answer
from .locks import SEARCH_LOCK, SearchBusy, search_slot
from .llm import BudgetExceeded, LLMInterrupted, LLMRefusal, get_llm, task_model
from .search import search_aspects
from .semantic_cache import get_cached_answer, set_cached_answer
from .verifier import verify_legal

logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 2000
EFFORTS = {"low", "medium", "high"}
# Ichki Qdrant va GPU modellari bir vaqtda bitta qidiruvni bajaradi (fondagi ish tahlili bilan umumiy qulf);
# LLM stream esa parallel ketaveradi.
_search_lock = SEARCH_LOCK


def warmup():
    from .models_runtime import get_embedder, get_reranker
    from .store import get_client

    t0 = time.monotonic()
    with _search_lock:
        get_embedder().encode(["isitish"])
        get_reranker().score("isitish", ["isitish"])
        get_client()
    logger.warning("RAG modellari yuklandi: %.1f s", time.monotonic() - t0)


def _event(name: str, data) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@require_GET
@login_required
@ensure_csrf_cookie
def chat_page(request):
    # Javob tili tanlagichi: har bir til o'z yozuvida (interfeys til almashtirgichi bilan bir xil nomlar)
    names = dict(settings.LANGUAGES)
    return render(request, "rag/chat.html", {
        "answer_languages": [(code, names[to_django_code(code)]) for code in LANG_NAMES]})




def _answer_stream(question: str, lang: str, effort: str, on_date: date | None = None, ui_lang: str | None = None,
                   owner=None):
    # Oqim javob qaytgandan keyin ishlaydi — xabarlar foydalanuvchi interfeys tilida bo'lishi uchun qayta yoqiladi.
    with translation.override(ui_lang or settings.LANGUAGE_CODE):
        yield from _answer_events(question, lang, effort, on_date, owner)


def _answer_events(question: str, lang: str, effort: str, on_date: date | None = None, owner=None):
    """Savolga javob beradi; xato bilan tugasa (qidiruv/LLM/byudjet) band qilingan savol kvotasi qaytariladi."""
    last = ""
    for event in _answer_core(question, lang, effort, on_date, owner):
        last = event
        yield event
    if owner is not None and last.startswith("event: error"):
        try:
            quota.refund_chat(owner)
        except Exception:
            logger.exception("Savol kvotasini qaytarib bo'lmadi")


LLM_STREAM_ATTEMPTS = 2   # provayder oqim o'rtasida uzilsa (masalan, Gemini 503 "high demand") — bir marta qayta urinish


def _llm_stream(parts: list[str], system: str, user: str, **kwargs):
    """LLM matnini bo'lak-bo'lak beradi (`parts` ga ham yig'adi). Oqim yarim yo'lda uzilsa (LLMInterrupted) — avval
    yuborilgan matn bekor qilinadi (`None` belgisi: mijozga `reset`) va so'rov qayta yuboriladi; ikkinchi urinish ham
    uzilsa — LLMInterrupted ko'tariladi. Shunda foydalanuvchi kesilgan javobni to'liq deb o'ylab qolmaydi."""
    for attempt in range(LLM_STREAM_ATTEMPTS):
        started = False
        try:
            for chunk in get_llm().stream_text(system, user, **kwargs):
                if chunk:
                    started = True
                    parts.append(chunk)
                    yield chunk
            return
        except LLMInterrupted:
            if attempt == LLM_STREAM_ATTEMPTS - 1:
                raise
            logger.warning("LLM oqimi uzildi — qayta urinish (%s)", attempt + 1)
            if started:
                parts.clear()
                yield None
            time.sleep(1.5)


SMALLTALK_SYSTEM = """Sen MEZON AI — Oʻzbekiston qonunchiligi boʻyicha advokatlarga yordam beradigan yuridik yordamchisan.
Foydalanuvchi savoli huquqqa tegishli emas (salomlashuv, tanishuv, "nima qila olasan", minnatdorchilik va h.k.).
Tabiiy, qisqa (1-3 gap) va har safar oʻz soʻzlaring bilan javob ber — tayyor andoza gaplarni takrorlama.
Salomga salom ber, minnatdorchilikka iltifot bilan javob ber. "Nima qila olasan" desa — qonun moddalarini lex.uz asosida
iqtibos bilan izohlash, ish hujjatlarini tahlil qilish, hujjat shablonlari borligini oʻz soʻzlaring bilan ayt.
Huquqqa aloqasiz boshqa mavzuda (ob-havo, matematika, retsept va h.k.) javob bermasdan, mutaxassisliging
qonunchilik ekanini mehr bilan ayt va huquqiy savol berishga taklif qil.
Qonun moddalari, modda raqamlari yoki iqtiboslarni OʻYLAB TOPMA, [M#] havolalarini yozma."""


def _smalltalk_events(question: str, lang: str, owner, t_search: float):
    """Huquqiy boʻlmagan savol: manbasiz, qisqa AI javobi. Savol kvotasi qaytariladi (huquqiy tahlil boʻlmadi)."""
    yield _event("aspects", [{"topic": "Muloqot", "queries": []}])
    yield _event("sources", [])
    system = f"{SMALLTALK_SYSTEM}\nJavobni {LANG_NAMES.get(lang, LANG_NAMES['uz-Latn'])} yoz."
    meta: dict = {}
    t1 = time.monotonic()
    first_token = None
    try:
        for chunk in _llm_stream([], system, question, effort="low", max_tokens=400, meta=meta,
                                 model=task_model("answer")):
            if chunk is None:
                first_token = None
                yield _event("reset", {})
                continue
            if first_token is None:
                first_token = time.monotonic() - t1
            text_out = lat_to_new_latn(chunk) if lang == "uz-Latn-2026" else chunk
            yield _event("delta", {"text": text_out})
    except BudgetExceeded as e:
        logger.warning("LLM byudjeti tugadi: %s", e)
        yield _event("error", {"message": _("AI xizmati hozircha band. Keyinroq qayta urinib koʻring.")})
        return
    except LLMInterrupted:
        yield _event("error", {"message": _("AI xizmati javobni oxirigacha yubora olmadi. Savolni qayta yuboring.")})
        return
    except Exception:
        logger.exception("Suhbat javobida LLM xatosi")
        yield _event("error", {"message": _("Javob yaratishda xato yuz berdi.")})
        return
    if owner is not None:
        try:
            if meta.get("cost_usd"):
                quota.record_cost(owner, meta["cost_usd"])
            quota.refund_chat(owner)
        except Exception:
            logger.exception("Suhbat kvotasi/xarajati yozilmadi")
    yield _event("verification", {"ok": True, "citations": [], "quotes_checked": 0, "issues": []})
    yield _event("done", {"timings": {"search_s": round(t_search, 2), "first_token_s": round(first_token or 0, 2),
                                      "answer_s": round(time.monotonic() - t1, 2)}, "usage": meta})


def _answer_core(question: str, lang: str, effort: str, on_date: date | None = None, owner=None):
    t0 = time.monotonic()

    # 0. Semantik kesh (Qdrant mezon_semantic_cache) — o'xshash savol bo'lsa darhol javob berish
    cached = get_cached_answer(question, lang, effort, on_date)
    if cached is not None:
        yield _event("aspects", cached["aspects"])
        yield _event("sources", cached["sources"])
        words = cached["answer"].split(" ")
        for i in range(0, len(words), 8):
            piece = " ".join(words[i:i + 8]) + " "
            text_out = lat_to_new_latn(piece) if lang == "uz-Latn-2026" else piece
            yield _event("delta", {"text": text_out})
        yield _event("verification", cached["verification"])
        yield _event("done", {
            "timings": {"search_s": 0.01, "first_token_s": 0.01, "answer_s": round(time.monotonic() - t0, 2)},
            "usage": {**cached.get("usage", {}), "cost_usd": 0.0, "cached": True, "similarity": cached["similarity"]},
        })
        return

    try:
        # Qonun iqtiboslari javob tilidagi rasmiy lex.uz matnidan (TZ §5.4): kirill/rus; qoraqalpoq va inglizda — lotin.
        # Qulf faqat GPU/Qdrant qismida (search_aspects ichida), LLM chaqiruvlari qulfdan tashqarida.
        hits, aspects = search_aspects(question, effort=effort, on_date=on_date, lang=corpus_lang(lang),
                                       slot=search_slot)
    except SearchBusy:
        yield _event("error", {"message": _("Server band — bir ozdan keyin qayta urinib koʻring.")})
        return
    except Exception:
        logger.exception("Qidiruv xatosi")
        yield _event("error", {"message": _("Qidiruvda xato yuz berdi.")})
        return
    t_search = time.monotonic() - t0
    if not hits and not aspects:
        # Savol huquqqa aloqasiz (LLM rejalovchisi aniqladi): lex.uz da qidirilmaydi, javobni AI o'zi yozadi
        yield from _smalltalk_events(question, lang, owner, t_search)
        return
    sources = build_sources(hits)
    serialized_sources = [
        {"key": s.key, "topic": s.hit.topic, "doc_title": s.hit.doc_title, "label": s.hit.label, "lex_url": s.hit.lex_url,
         "edition": s.hit.payload.get("edition", ""), "exact": s.hit.exact, "as_of": s.hit.as_of}
        for s in sources
    ]
    yield _event("aspects", aspects)
    yield _event("sources", serialized_sources)
    if not sources:
        yield _event("error", {"message": _("Mos qonun moddalari topilmadi.")})
        return

    system, user = build_prompt(question, sources, lang)
    meta: dict = {}
    parts: list[str] = []
    t1 = time.monotonic()
    first_token = None
    try:
        for chunk in _llm_stream(parts, system, user, effort=effort, meta=meta, model=task_model("answer")):
            if chunk is None:   # oqim uzildi va qayta boshlandi — mijoz yarim matnni tozalaydi
                first_token = None
                yield _event("reset", {})
                continue
            if first_token is None:
                first_token = time.monotonic() - t1
            text_out = lat_to_new_latn(chunk) if lang == "uz-Latn-2026" else chunk
            yield _event("delta", {"text": text_out})
    except LLMRefusal:
        yield _event("error", {"message": _("Model bu so'rovga javob berishni rad etdi.")})
        return
    except BudgetExceeded as e:
        # Chegara miqdori va sozlama nomi foydalanuvchiga ko'rsatilmaydi — faqat logga
        logger.warning("LLM byudjeti tugadi: %s", e)
        yield _event("error", {"message": _("AI xizmati hozircha band. Keyinroq qayta urinib koʻring.")})
        return
    except LLMInterrupted:
        yield _event("error", {"message": _("AI xizmati javobni oxirigacha yubora olmadi. Savolni qayta yuboring.")})
        return
    except Exception:
        logger.exception("LLM xatosi")
        yield _event("error", {"message": _("Javob yaratishda xato yuz berdi.")})
        return

    if owner is not None and meta.get("cost_usd"):   # AI xarajat radari (admin panel): savol narxi kunlik sarfga
        try:
            quota.record_cost(owner, meta["cost_usd"])
        except Exception:
            logger.exception("Chat xarajatini yozib bo'lmadi")
    report = verify_answer("".join(parts), sources)
    try:
        report.issues += verify_legal("".join(parts), sources, on_date)
    except Exception:  # bazaviy tekshiruv xatosi javobni buzmasin — logga yoziladi
        logger.exception("verify_legal xatosi")

    verification_data = {
        "ok": report.ok, "citations": report.citations, "quotes_checked": report.quotes_checked,
        "issues": [{"severity": i.severity, "kind": i.kind, "detail": i.detail} for i in report.issues],
    }

    if report.ok and parts:
        try:
            set_cached_answer(
                question=question, lang=lang, effort=effort, aspects=aspects,
                sources=serialized_sources, answer="".join(parts),
                verification=verification_data, usage=meta, on_date=on_date,
            )
        except Exception:
            logger.exception("Semantik keshga yozishda xato")

    yield _event("verification", verification_data)
    yield _event("done", {
        "timings": {"search_s": round(t_search, 2), "first_token_s": round(first_token or 0, 2),
                    "answer_s": round(time.monotonic() - t1, 2)},
        "usage": meta,
    })


class AskError(ValueError):
    pass


def parse_ask(body: dict) -> tuple[str, str, str, date | None]:
    """So'rov tanasi -> (savol, javob tili, effort, voqea sanasi). Xato bo'lsa — AskError (foydalanuvchi tilida)."""
    question = str(body.get("question", "")).strip()
    lang = body.get("lang", "uz-Latn")
    effort = body.get("effort", "medium")
    try:  # ixtiyoriy voqea sanasi: qonun o'sha sanadagi tahrirda olinadi
        on_date = date.fromisoformat(body["on_date"]) if body.get("on_date") else None
    except (TypeError, ValueError):
        raise AskError(_("on_date YYYY-MM-DD koʻrinishida boʻlsin"))
    if not question or len(question) > MAX_QUESTION_CHARS:
        raise AskError(_("Savol 1–%(max)s belgi bo'lishi kerak") % {"max": MAX_QUESTION_CHARS})
    if lang not in LANG_NAMES or effort not in EFFORTS:
        raise AskError(_("Noto'g'ri lang yoki effort"))
    return question, lang, effort, on_date


def answer_response(question: str, lang: str, effort: str, on_date: date | None, owner=None) -> StreamingHttpResponse:
    """SSE javob (kvota band qilingandan keyin). HTML chat va API v1 uchun umumiy."""
    response = StreamingHttpResponse(_answer_stream(question, lang, effort, on_date, translation.get_language(), owner),
                                     content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # nginx orqasida buferlanmasin
    return response


@require_POST
@api_login_required
def ask(request):
    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest(_("JSON kutilgan"))
    try:
        question, lang, effort, on_date = parse_ask(body)
    except AskError as e:
        return HttpResponseBadRequest(str(e))
    decision = quota.reserve_chat(request.user)   # tarif: kunlik/umrbod savol limiti (TZ §8.1)
    if not decision.ok:
        return HttpResponse(decision.message, status=429)
    return answer_response(question, lang, effort, on_date, request.user)
