"""/api/v1/templates/* — shablonli hujjatlar (AI siz, TZ §5.1.1).

Ko'rib chiqish (preview) bepul; DOCX/PDF yuklab olish tarif kvotasini band qiladi (bepul tarifda — belgi bilan).
To'ldirilgan ma'lumotlar (F.I.Sh., JSHSHIR, pasport) saqlanmaydi va logga yozilmaydi.
"""
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import quota
from apps.doc_builder.models import DocumentTemplate
from apps.doc_builder.rendering import fill
from apps.doc_builder.views import FORMATS, file_response

from .. import serializers as s
from .cases import FILE_RESPONSE
from .common import error, raise_form_errors


def _published(template_id) -> DocumentTemplate:
    return get_object_or_404(DocumentTemplate, pk=template_id, is_published=True)


def _filled_blocks(template: DocumentTemplate, data) -> list:
    values = data.get("values") if isinstance(data.get("values"), dict) else {}
    lang = data.get("lang")
    # Django forma satrlarni kutadi: raqam/sana JSON da qanday kelsa ham satrga o'tkaziladi
    form, blocks = fill(template, {k: "" if v is None else str(v) for k, v in values.items()}, lang=lang)
    if blocks is None:
        raise_form_errors(form)
    return blocks


class TemplateListView(generics.ListAPIView):
    serializer_class = s.TemplateSerializer
    pagination_class = None

    def get_serializer_context(self):
        context = super().get_serializer_context()
        lang = self.request.query_params.get("lang")
        if lang:
            context["lang"] = lang
        return context

    def get_queryset(self):
        qs = DocumentTemplate.objects.filter(is_published=True)
        category = self.request.query_params.get("category")
        subcategory = self.request.query_params.get("subcategory")
        if category:
            qs = qs.filter(category=category)
        if subcategory:
            qs = qs.filter(subcategory_slug=subcategory)
        return qs

    @extend_schema(parameters=[
        OpenApiParameter("category", str, description="CONTRACTS, STATEMENTS, PERSONAL, NOTARIAL, COURT, CORPORATE, …"),
        OpenApiParameter("subcategory", str, description="Subcategory slug (e.g. court-claims, real-estate-contracts)"),
        OpenApiParameter("lang", str, description="Hujjat tili (uz-Latn, uz-Cyrl, ru)"),
    ], tags=["templates"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TemplateDetailView(APIView):
    @extend_schema(parameters=[
        OpenApiParameter("lang", str, description="Hujjat tili (uz-Latn, uz-Cyrl, ru)"),
    ], responses=s.TemplateDetailSerializer, tags=["templates"],
                   description="form_schema: [{name, label, type, required, options, help}]")
    def get(self, request, template_id):
        lang = request.query_params.get("lang")
        template = _published(template_id)
        return Response(s.TemplateDetailSerializer(template, context={"request": request, "lang": lang}).data)


class TemplatePreviewView(APIView):
    @extend_schema(request=s.TemplateValuesSerializer, responses=s.PreviewSerializer, tags=["templates"])
    def post(self, request, template_id):
        blocks = _filled_blocks(_published(template_id), request.data)
        return Response({"blocks": [{"kind": b.kind, "text": b.text} for b in blocks]})


class TemplateRenderView(APIView):
    @extend_schema(request=s.TemplateValuesSerializer, responses={200: FILE_RESPONSE, 400: s.DetailSerializer,
                                                                429: s.DetailSerializer}, tags=["templates"])
    def post(self, request, template_id, fmt):
        template = _published(template_id)
        if fmt not in FORMATS:
            return error("docx | pdf", 404, "format")
        blocks = _filled_blocks(template, request.data)
        decision = quota.reserve_template(request.user)   # faqat DOCX/PDF yuklab olish hisoblanadi
        if not decision.ok:
            return error(decision.message, 429, f"quota_{decision.code}")
        return file_response(template, blocks, fmt, decision.plan.watermark)
