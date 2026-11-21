"""Django dev serveri LLM siz — frontend ishlab chiqish va API sinovlari uchun (Claude API ga pul ketmaydi).

    .venv\\Scripts\\python tools\\dev_nollm.py [port]        # sukut: 8011

LLM provayderi yopiq portga yo'naltiriladi: ish tahlili va chat javobi darhol "xato" bilan tugaydi (kvota
qaytariladi), qolgan hamma narsa (auth, yuklash, holat, hisobotlar, shablonlar, qidiruv) odatdagidek ishlaydi.
Baza va fayllar — asosiy dev server bilan umumiy (data/). Qdrant kerak bo'lsa alohida ishga tushiring.
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]



def disable_llm() -> None:
    """LLM ni o'chiradi (Django yuklanishidan oldin chaqiriladi). tools/serve.py --nollm ham shuni ishlatadi."""
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_URL"] = "http://127.0.0.1:9"     # hech kim tinglamaydi -> ulanish darhol rad etiladi
    os.environ["MEZON_ANTHROPIC_API_KEY"] = "disabled"
    os.environ.setdefault("RAG_WARMUP", "0")            # GPU modellari faqat qidiruv so'ralganda yuklanadi


if __name__ == "__main__":
    disable_llm()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    # Expo veb-rejimi (Metro :8081) boshqa origin dan so'raydi — CORS (mobil ilova Bearer token bilan, cookie siz)
    os.environ.setdefault("DJANGO_CORS_ORIGINS", "http://localhost:8081,http://127.0.0.1:8081")
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    from django.core.management import execute_from_command_line

    port = sys.argv[1] if len(sys.argv) > 1 else "8011"
    execute_from_command_line(["manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"])
