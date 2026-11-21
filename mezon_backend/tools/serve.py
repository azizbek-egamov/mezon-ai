"""MEZON production serveri (Windows): waitress WSGI, faqat 127.0.0.1 da — tashqaridan Cloudflare Tunnel orqali.

    .venv\\Scripts\\python tools\\serve.py [--port 8010] [--threads 16] [--nollm] [--trycloudflare] [--http]

- Har doim DJANGO_DEBUG=0 (production sozlamalari: HTTPS proksi, HSTS, eski UI o'chiq, SPA /, /panel/).
- Oldin: `manage.py collectstatic --noinput` (tools/prod.ps1 start buni o'zi qiladi) va frontend `npm run build`.
- --nollm: LLM o'chiq (dev_nollm kabi) — tunnel/HTTPS sinovi uchun, Claude API ga pul ketmaydi.
- SSE chat har oqim uchun bitta ip (thread) band qiladi — threads soni bir vaqtdagi suhbatlardan ko'p bo'lsin.
Ish tahlili navbati (apps/cases/worker.py) shu jarayon ichida ishlaydi, shuning uchun jarayon bitta bo'lishi kerak.
"""
import argparse
import os
import sys
import threading
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="MEZON production serveri (waitress)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MEZON_PORT", "8010")))
    parser.add_argument("--threads", type=int, default=int(os.environ.get("MEZON_THREADS", "16")))
    parser.add_argument("--nollm", action="store_true", help="LLM siz (sinov uchun)")
    parser.add_argument("--trycloudflare", action="store_true",
                        help="vaqtinchalik quick tunnel (*.trycloudflare.com) domenlariga ruxsat — faqat sinov uchun")
    parser.add_argument("--http", action="store_true",
                        help="USB (adb reverse) uchun: HTTPS ga yo'naltirish va HSTS o'chiq — faqat 127.0.0.1 ichida")
    args = parser.parse_args()

    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    if args.nollm:
        sys.path.insert(0, str(BACKEND / "tools"))
        from dev_nollm import disable_llm

        disable_llm()
    os.environ["DJANGO_DEBUG"] = "0"
    if args.trycloudflare:  # `cloudflared tunnel --url http://127.0.0.1:<port>` beradigan tasodifiy domen
        os.environ["DJANGO_ALLOWED_HOSTS"] = "localhost,127.0.0.1,.trycloudflare.com"
        os.environ["DJANGO_CSRF_TRUSTED_ORIGINS"] = "https://*.trycloudflare.com"
    if args.http:  # telefondagi http://localhost:<port> -> adb reverse -> shu server; trafik USB kabel ichida
        os.environ["DJANGO_SSL_REDIRECT"] = "0"
        os.environ["DJANGO_HSTS_SECONDS"] = "0"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from django.conf import settings
    from django.core.wsgi import get_wsgi_application
    from waitress import serve

    application = get_wsgi_application()
    if os.environ.get("RAG_WARMUP", "1") == "1":  # modellar fonda yuklanadi — birinchi savol kutmasin
        from apps.rag.views import warmup

        threading.Thread(target=warmup, name="rag-warmup", daemon=True).start()

    print(f"MEZON (production{', LLM siz' if args.nollm else ''}): http://127.0.0.1:{args.port}/  "
          f"ip: {args.threads}", flush=True)
    serve(
        application,
        host="127.0.0.1",                 # faqat lokal: tashqi ulanish — faqat cloudflared orqali
        port=args.port,
        threads=args.threads,
        ident="MEZON",                    # Server sarlavhasida waitress versiyasi ko'rinmasin
        # cloudflared 127.0.0.1 dan ulanadi: uning X-Forwarded-Proto sarlavhasiga ishonamiz (aks holda waitress uni
        # o'chiradi va HTTPS so'rov ham HTTP deb qayta yo'naltiriladi). Mijoz IP — CF-Connecting-IP (lockout.client_ip).
        trusted_proxy="127.0.0.1",
        trusted_proxy_headers={"x-forwarded-proto"},
        clear_untrusted_proxy_headers=True,
        channel_timeout=300,              # uzun SSE javoblar (qidiruv + LLM) uzilmasin
        max_request_body_size=(settings.CASE_MAX_MB + 5) * 1024 * 1024,
    )


if __name__ == "__main__":
    main()
