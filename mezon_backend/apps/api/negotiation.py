from rest_framework.exceptions import NotAcceptable
from rest_framework.negotiation import DefaultContentNegotiation


class LenientNegotiation(DefaultContentNegotiation):
    """Mijoz `Accept: text/event-stream` yoki `application/pdf` yuborsa ham 406 qaytarmaymiz: bunday view lar
    o'zi StreamingHttpResponse/FileResponse qaytaradi, xato bo'lsa — JSON (birinchi renderer)."""

    def select_renderer(self, request, renderers, format_suffix=None):
        try:
            return super().select_renderer(request, renderers, format_suffix)
        except NotAcceptable:
            if format_suffix or request.query_params.get(self.settings.URL_FORMAT_OVERRIDE):
                raise
            return renderers[0], renderers[0].media_type
