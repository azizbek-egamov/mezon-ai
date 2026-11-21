"""/api/v1/cases/* — ish yuklash, holat, hisobot, PDF, yuridik tasdiq (TZ §12), eksport, o'chirish, qayta urinish.

Har bir foydalanuvchi faqat o'z ishlarini ko'radi — begona ish so'ralsa 404 (ish borligi ham oshkor qilinmaydi).
Mantiq — `apps/cases/services.py` (HTML sahifalar bilan umumiy). Hisobot, PDF va eksport `no-store`.
"""
import io

from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cases import services
from apps.cases.case_types import CASE_TYPES
from apps.cases.models import CaseRun
from apps.cases.services import CaseError

from .. import serializers as s
from .common import case_error, error, no_store

FILE_RESPONSE = OpenApiResponse(OpenApiTypes.BINARY, description="Fayl")


def own_run(request, run_id) -> CaseRun:
    return get_object_or_404(CaseRun, pk=run_id, owner=request.user)


class CaseOptionsView(APIView):
    @extend_schema(responses=s.CaseOptionsSerializer, tags=["cases"])
    def get(self, request):
        return Response({"case_types": [{"code": c, "label": str(t.label)} for c, t in CASE_TYPES.items()],
                         **services.upload_limits(request.user)})


class CaseListView(generics.ListAPIView):
    serializer_class = s.CaseSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return CaseRun.objects.filter(owner=self.request.user)

    @extend_schema(tags=["cases"])
    def get(self, request, *args, **kwargs):
        services.recover_interrupted()
        return super().get(request, *args, **kwargs)

    @extend_schema(request={"multipart/form-data": s.CaseUploadSerializer},
                   responses={201: s.CaseDetailSerializer, 400: s.DetailSerializer, 429: s.DetailSerializer},
                   tags=["cases"], description="Ko'p fayl: `files` maydoni takrorlanadi. 429 — tarif limiti.")
    def post(self, request):
        data = request.data
        try:
            run = services.create_case(request.user, request.FILES.getlist("files"),
                                       category=data.get("category", ""), title=data.get("title", ""),
                                       zero_retention=str(data.get("zero_retention", "")).lower() in ("1", "true", "on"))
        except CaseError as e:
            return case_error(e)
        return Response(s.CaseDetailSerializer(run).data, status=status.HTTP_201_CREATED)


class CaseDetailView(APIView):
    @extend_schema(responses=s.CaseDetailSerializer, tags=["cases"],
                   description="Holat va progress (tahlil paytida 2–3 s da bir so'rang)")
    def get(self, request, run_id):
        return Response(s.CaseDetailSerializer(own_run(request, run_id)).data)

    @extend_schema(responses={204: None, 409: s.DetailSerializer}, tags=["cases"],
                   description="Ishni butunlay o'chirish (PDF, hisobot, yozuv). Tahlil ketayotganda — 409.")
    def delete(self, request, run_id):
        try:
            services.delete_case(own_run(request, run_id))
        except CaseError as e:
            return case_error(e)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CaseRetryView(APIView):
    @extend_schema(request=None, responses={200: s.CaseDetailSerializer, 409: s.DetailSerializer,
                                            429: s.DetailSerializer}, tags=["cases"])
    def post(self, request, run_id):
        run = own_run(request, run_id)
        try:
            services.retry_case(request.user, run)
        except CaseError as e:
            return case_error(e)
        run.refresh_from_db()
        return Response(s.CaseDetailSerializer(run).data)


class CaseReportView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT, 409: s.DetailSerializer}, tags=["cases"],
                   description="Tayyor tahlil hisoboti (pipeline JSON). Tahlil tugamagan bo'lsa — 409.")
    def get(self, request, run_id):
        try:
            return no_store(Response(services.read_report(own_run(request, run_id))))
        except CaseError as e:
            return case_error(e)


class CasePdfView(APIView):
    @extend_schema(responses={200: FILE_RESPONSE, 404: s.DetailSerializer}, tags=["cases"],
                   description="Yuklangan ishning birlashtirilgan PDF i (deshifrlangan, keshlanmaydi)")
    def get(self, request, run_id):
        data = services.read_pdf(own_run(request, run_id))
        if data is None:
            return error(_("PDF oʻchirilgan yoki topilmadi"), 404, "pdf_deleted")
        response = FileResponse(io.BytesIO(data), content_type="application/pdf")
        response["Content-Disposition"] = "inline"
        return no_store(response)


class CaseConfirmationView(APIView):
    @extend_schema(responses={200: OpenApiTypes.OBJECT, 409: s.DetailSerializer}, tags=["cases"],
                   description="Tasdiq oynasi: keltirilgan moddalar, tasdiqlanmagan baholar, confirmed_at")
    def get(self, request, run_id):
        try:
            return no_store(Response(services.confirmation_info(own_run(request, run_id))))
        except CaseError as e:
            return case_error(e)

    @extend_schema(request=s.ConfirmSerializer, responses={200: s.CaseDetailSerializer, 400: s.DetailSerializer,
                                                         409: s.DetailSerializer}, tags=["cases"])
    def post(self, request, run_id):
        run = own_run(request, run_id)
        if request.data.get("acknowledged") not in (True, "true", "1", 1):
            return error(_("Tasdiqlash uchun belgini qoʻying"), 400, "not_acknowledged")
        try:
            services.confirm_case(run)
        except CaseError as e:
            return case_error(e)
        return Response(s.CaseDetailSerializer(run).data)


class CaseExportView(APIView):
    @extend_schema(responses={200: FILE_RESPONSE, 403: s.DetailSerializer, 409: s.DetailSerializer}, tags=["cases"],
                   description="Rasmiy DOCX/PDF — faqat \"tanishdim\" tasdig'idan keyin (aks holda 403)")
    def get(self, request, run_id, fmt):
        run = own_run(request, run_id)
        try:
            content, content_type, filename = services.export_file(run, fmt, request.user.full_name)
        except CaseError as e:
            return case_error(e)
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return no_store(response)
