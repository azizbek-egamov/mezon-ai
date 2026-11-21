"""/api/v1/laws/* — qonunchilik bazasini ko'rish (lex.uz korpusi): hujjatlar, moddalar, semantik qidiruv.

`lang` parametri — korpus matni tili: lat | cyr | ru (sukut — so'rov interfeys tilidan, `corpus_lang`). Modda bu
tilda bo'lmasa, asosiy tildagi matn qaytariladi (`lang` maydoni haqiqiy tilni ko'rsatadi).
Semantik qidiruv LLM chaqirmaydi (rewrite=False), lekin GPU modellari va Qdrant serverini ishlatadi.
"""
import logging

from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import translation
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.i18n.codes import to_tz_code
from apps.lex_corpus.models import LANGS, LegalActArticle, LegalActDocument, LegalActEdition, corpus_lang
from apps.lex_corpus.normalize import normalize_title

from .. import serializers as s
from ..throttling import ClientIpScopedRateThrottle
from .common import error

logger = logging.getLogger(__name__)
LANG_PARAM = OpenApiParameter("lang", str, enum=list(LANGS), description="Matn tili; sukut — interfeys tilidan")
MAX_SEARCH_LIMIT = 20


def _lang(request) -> str:
    lang = request.query_params.get("lang", "")
    return lang if lang in LANGS else corpus_lang(to_tz_code(translation.get_language() or ""))


def _doc_data(doc: LegalActDocument, lang: str) -> dict:
    lex_id = doc.lex_id_for(lang) or doc.primary_lex_id
    return {"abs_id": doc.abs_id, "title": doc.title_for(lang), "doc_type": doc.doc_type,
            "doc_type_label": doc.get_doc_type_display(), "official_number": doc.official_number,
            "adoption_date": doc.adoption_date, "status": doc.status, "status_label": doc.get_status_display(),
            "lex_url": f"https://lex.uz/uz/docs/{lex_id}",
            "languages": ["lat", *(code for code in ("cyr", "ru") if doc.has_lang(code))]}


class LawDocumentListView(generics.ListAPIView):
    """Matni bazada bor hujjatlar (yadro korpusi), nomi bo'yicha qidiruv."""
    serializer_class = s.LawDocumentSerializer

    def get_queryset(self):
        has_text = Exists(LegalActEdition.objects.filter(document=OuterRef("pk"), is_current=True))
        qs = LegalActDocument.objects.filter(has_text).order_by("-hierarchy_weight", "-adoption_date")
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title_search__icontains=normalize_title(q).lower()) | Q(title_uz_cyr__icontains=q)
                           | Q(title_ru__icontains=q) | Q(official_number__iexact=q))
        doc_type = self.request.query_params.get("doc_type")
        return qs.filter(doc_type=doc_type) if doc_type else qs

    @extend_schema(parameters=[OpenApiParameter("q", str, description="Nomi yoki raqami bo'yicha"),
                               OpenApiParameter("doc_type", str, description="CODE, LAW, PRES_DECREE, …"), LANG_PARAM],
                   tags=["laws"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        lang = _lang(request)
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(s.LawDocumentSerializer([_doc_data(d, lang) for d in page], many=True).data)


class LawDocumentDetailView(APIView):
    @extend_schema(parameters=[LANG_PARAM], responses=s.LawDocumentDetailSerializer, tags=["laws"],
                   description="Hujjat va joriy tahrirdagi moddalar ro'yxati (matnsiz)")
    def get(self, request, doc_id):
        lang = _lang(request)
        doc = get_object_or_404(LegalActDocument, pk=doc_id)
        edition = doc.editions.filter(is_current=True).first()
        if edition is None:
            return error(_("Bu hujjat matni bazada yoʻq"), 404, "no_text")
        articles = edition.articles.select_related("document", "edition").order_by("position")
        data = _doc_data(doc, lang) | {"edition": edition.edition_label, "articles": [
            {"id": a.pk, "unit_type": a.unit_type, "article_number": a.article_number,
             "label": a.lang_label(lang if a.has_lang(lang) else a.source_lang),
             "section_path": a.section_in(lang if a.has_lang(lang) else a.source_lang)} for a in articles]}
        return Response(s.LawDocumentDetailSerializer(data).data)


class ArticleView(APIView):
    @extend_schema(parameters=[LANG_PARAM], responses=s.ArticleSerializer, tags=["laws"])
    def get(self, request, article_id):
        a = get_object_or_404(LegalActArticle.objects.select_related("document", "edition"), pk=article_id)
        lang = _lang(request)
        if not a.has_lang(lang):
            lang = a.source_lang
        data = {"id": a.pk, "document_id": a.document_id, "doc_title": a.document.title_for(lang), "lang": lang,
                "unit_type": a.unit_type, "article_number": a.article_number, "label": a.lang_label(lang),
                "section_path": a.section_in(lang), "text": a.text_in(lang),
                "parts": [{"n": str(p.get("n", "")), "text": p.get("text", "")} for p in a.parts_in(lang)],
                "edition": a.edition.edition_label, "is_current": a.edition.is_current,
                "valid_from": a.valid_from, "valid_until": a.valid_until, "lex_url": a.url_in(lang)}
        return Response(s.ArticleSerializer(data).data)


class LawSearchView(APIView):
    throttle_classes = [ClientIpScopedRateThrottle]   # GPU qulfini band qilib hammani to'sishdan himoya
    throttle_scope = "laws_search"

    @extend_schema(parameters=[OpenApiParameter("q", str, required=True), LANG_PARAM,
                               OpenApiParameter("limit", int, description=f"1–{MAX_SEARCH_LIMIT}, sukut 10")],
                   responses={200: s.SearchHitSerializer(many=True), 503: s.DetailSerializer}, tags=["laws"],
                   description="Gibrid qidiruv (bge-m3 + Qdrant + reranker), LLM siz. 'JK 168-modda' — aniq havola.")
    def get(self, request):
        from apps.rag.locks import SearchBusy, search_slot
        from apps.rag.search import search

        q = request.query_params.get("q", "").strip()
        if not q or len(q) > 500:
            return error(_("Soʻrov 1–500 belgi boʻlsin"), 400, "invalid")
        try:
            limit = min(max(int(request.query_params.get("limit", 10)), 1), MAX_SEARCH_LIMIT)
        except ValueError:
            limit = 10
        try:
            with search_slot():
                hits = search(q, limit=limit, rewrite=False, lang=_lang(request))
        except SearchBusy:
            return error(_("Server band — bir ozdan keyin qayta urinib koʻring."), 503, "search_busy")
        except Exception:
            logger.exception("Qidiruv xatosi")
            return error(_("Qidiruvda xato yuz berdi."), 503, "search_unavailable")
        return Response([{"article_id": h.article_id, "document_id": h.document_id, "doc_title": h.doc_title,
                          "label": h.label, "text": h.text, "lex_url": h.lex_url,
                          "edition": h.payload.get("edition", ""), "exact": h.exact, "score": round(h.score, 4)}
                         for h in hits])
