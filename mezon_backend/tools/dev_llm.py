"""Django dev serveri — haqiqiy LLM (`.env` dagi LLM_PROVIDER, hozir Gemini) bilan, frontend/mobil veb sinovi uchun.

    .venv\\Scripts\\python tools\\dev_llm.py [port]        # sukut: 8011

`dev_nollm.py` bilan bir xil port va CORS (Vite proxy `/api` -> :8011, Expo veb-rejimi :8081), lekin LLM o'chirilmaydi:
savol-javob va ish tahlili `.env` dagi provayderga (Gemini) boradi — PULLIK/API chaqiruvlari. Qdrant alohida ishga tushiriladi.
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("DJANGO_CORS_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081")
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    from django.core.management import execute_from_command_line

    port = sys.argv[1] if len(sys.argv) > 1 else "8011"
    execute_from_command_line(["manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"])
