"""LLM provayder adapteri (TZ §3.2 LLMProvider).

Provayder `.env` dagi LLM_PROVIDER bilan tanlanadi (ollama | anthropic); qolgan kod faqat
`get_llm().chat_json(...)` ni chaqiradi. Har bir provayder token sarfini `usage` da yig'adi.
"""
import json
import logging
import os
import threading
from datetime import datetime
from dataclasses import dataclass
from functools import lru_cache

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class Usage:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0

    def cost_usd(self, price_in: float, price_out: float, price_cache_read: float) -> float:
        """Narxlar — 1 mln token uchun dollar."""
        return (self.input_tokens * price_in + self.output_tokens * price_out
                + self.cache_read_tokens * price_cache_read) / 1_000_000


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model, self.base_url = model, base_url
        self.usage = Usage()

    def chat_json(self, system: str, user: str, schema: dict | None = None, effort: str | None = None,
                  timeout: int = 300, max_tokens: int = 4096, model: str | None = None) -> dict:
        resp = requests.post(f"{self.base_url}/api/chat", timeout=timeout, json={
            "model": model or self.model, "stream": False, "format": schema or "json",
            "options": {"temperature": 0, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        resp.raise_for_status()
        data = resp.json()
        self.usage.requests += 1
        self.usage.input_tokens += data.get("prompt_eval_count", 0)
        self.usage.output_tokens += data.get("eval_count", 0)
        return json.loads(data["message"]["content"])

    def stream_text(self, system: str, user: str, effort: str | None = None, max_tokens: int = 4096,
                    meta: dict | None = None, model: str | None = None):
        # model — AnthropicProvider bilan bir xil imzo (task_model ollama da None qaytaradi)
        resp = requests.post(f"{self.base_url}/api/chat", stream=True, timeout=300, json={
            "model": model or self.model, "stream": True, "options": {"temperature": 0, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        })
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("done"):
                self.usage.requests += 1
                self.usage.input_tokens += chunk.get("prompt_eval_count", 0)
                self.usage.output_tokens += chunk.get("eval_count", 0)
                self.last_stop_reason = chunk.get("done_reason")
                if meta is not None:
                    meta.update(input_tokens=chunk.get("prompt_eval_count", 0), output_tokens=chunk.get("eval_count", 0),
                                stop_reason=chunk.get("done_reason"), cost_usd=0.0)
                break
            yield chunk.get("message", {}).get("content", "")

    def unload(self):
        """Modelni VRAM dan bo'shatish (8 GB kartada embedding/reranker uchun joy ochadi)."""
        requests.post(f"{self.base_url}/api/generate", json={"model": self.model, "keep_alive": 0}, timeout=60)

    def transcribe_image(self, image_bytes: bytes, mime_type: str = "image/jpeg",
                         system: str = "", prompt: str = "", timeout: int = 120,
                         max_tokens: int = 8192, model: str | None = None) -> tuple[str, float]:
        import base64
        b64_image = base64.b64encode(image_bytes).decode("ascii")
        prompt_text = prompt or "Ushbu hujjat tasviridagi barcha matnlarni 100% aslidagidek birga-bir ko'chirib ber."
        resp = requests.post(f"{self.base_url}/api/chat", timeout=timeout, json={
            "model": model or self.model, "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
            "messages": [
                *([{"role": "system", "content": system}] if system else []),
                {"role": "user", "content": prompt_text, "images": [b64_image]}
            ],
        })
        resp.raise_for_status()
        data = resp.json()
        text = data.get("message", {}).get("content", "")
        self.usage.requests += 1
        self.usage.input_tokens += data.get("prompt_eval_count", 0)
        self.usage.output_tokens += data.get("eval_count", 0)
        return text, 0.0


# 1 mln token narxi (input, output, cache read), 2026-10 holatiga.
ANTHROPIC_PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.10),  # cache narxi aniqlanmagan — yuqori baho
}


class LLMRefusal(Exception):
    pass


class LLMInterrupted(Exception):
    """Javob oqimi yarim yo'lda uzildi (provayder oqim ichida xato qaytardi, ulanish uzildi yoki tugash belgisi yo'q).
    Oqim boshlangan bo'lsa matn to'liq emas — chaqiruvchi qayta urinishi yoki xato ko'rsatishi kerak."""


class BudgetExceeded(Exception):
    """Jarayon uchun belgilangan xarajat chegarasi (LLM_BUDGET_USD) tugadi — keyingi chaqiruv yuborilmaydi."""


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str, base_url: str):
        import anthropic  # ixtiyoriy bog'liqlik: faqat shu provayder tanlanganda kerak

        if not api_key:
            raise ValueError(".env da ANTHROPIC_API_KEY yo'q")
        # Kalit va manzil aniq beriladi: SDK umumiy ANTHROPIC_* muhit o'zgaruvchilarini olmasin.
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.model = model
        self.usage = Usage()
        self.spent_usd = 0.0
        self.budget_usd = settings.LLM_BUDGET_USD  # 0 = cheklovsiz
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._inflight = 0
        self._reserved_usd = 0.0

    def _begin(self, model: str, prompt_chars: int, max_tokens: int) -> float:
        """Chaqiruvdan oldin uning eng yuqori narxini band qiladi. Band qilinganlar bilan chegaradan oshsa —
        parallel chaqiruvlar tugashini kutadi va haqiqiy sarf bilan qayta tekshiradi. Natijada chegaradan oshish
        ko'pi bilan bitta chaqiruv narxicha bo'ladi (u yolg'iz ishlayotgan bo'lsa)."""
        price_in, price_out, _ = ANTHROPIC_PRICES.get(model, (0, 0, 0))
        worst = (prompt_chars / 2 * price_in + max_tokens * price_out) / 1e6  # o'zbekcha: ~2 belgi/token (yuqori baho)
        with self._cond:
            if self.budget_usd:
                while self._inflight and self.spent_usd + self._reserved_usd + worst > self.budget_usd:
                    self._cond.wait()
                if self.spent_usd >= self.budget_usd:
                    raise BudgetExceeded(f"Xarajat chegarasi tugadi: ${self.spent_usd:.4f} / ${self.budget_usd:.2f}")
            self._inflight += 1
            self._reserved_usd += worst
        return worst

    def extend_budget(self, amount: float) -> None:
        """Bitta katta vazifa (masalan, ish tahlili) uchun jarayon chegarasini oshirish."""
        with self._cond:
            if self.budget_usd:
                self.budget_usd = max(self.budget_usd, self.spent_usd) + amount
            self._cond.notify_all()

    def _end(self, reserved: float) -> None:
        with self._cond:
            self._inflight -= 1
            self._reserved_usd -= reserved
            self._cond.notify_all()

    def chat_json(self, system: str, user: str, schema: dict | None = None, effort: str | None = None,
                  timeout: int = 300, max_tokens: int = 4096, model: str | None = None) -> dict:
        model = model or self.model
        output_config: dict = {"effort": effort or "medium"}
        if schema:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        reserved = self._begin(model, len(system) + len(user), max_tokens)
        try:
            response = self.client.with_options(timeout=timeout).messages.create(
                model=model, max_tokens=max_tokens, system=system, output_config=output_config,
                messages=[{"role": "user", "content": user}],
            )
            self._account(model, response.usage)
        finally:
            self._end(reserved)
        if response.stop_reason == "refusal":
            raise LLMRefusal(getattr(response.stop_details, "category", None))
        if response.stop_reason == "max_tokens":
            raise ValueError(f"Javob max_tokens={max_tokens} ga yetib kesildi")
        text = next((b.text for b in response.content if b.type == "text"), "{}")
        return json.loads(text)

    def _account(self, model: str, u) -> None:
        """Token va xarajat hisobi (bir nechta oqimdan chaqirilishi mumkin)."""
        price_in, price_out, price_cache = ANTHROPIC_PRICES.get(model, (0, 0, 0))
        cache_read = getattr(u, "cache_read_input_tokens", 0) or 0
        cost = (u.input_tokens * price_in + u.output_tokens * price_out + cache_read * price_cache) / 1e6
        with self._lock:
            self.usage.requests += 1
            self.usage.input_tokens += u.input_tokens
            self.usage.output_tokens += u.output_tokens
            self.usage.cache_read_tokens += cache_read
            self.spent_usd += cost
            # Har bir chaqiruv jurnali — Console hisobi bilan solishtirish uchun.
            with open(settings.DATA_DIR / "llm_usage.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "model": model,
                                     "in": u.input_tokens, "out": u.output_tokens, "cache_read": cache_read,
                                     "usd": round(cost, 6)}) + "\n")

    def stream_text(self, system: str, user: str, effort: str | None = None, max_tokens: int = 16000,
                    meta: dict | None = None, model: str | None = None):
        """Javob matnini bo'lak-bo'lak qaytaradi (generator). Tugagach umumiy usage va `meta` (shu so'rovning
        input_tokens, output_tokens, stop_reason, cost_usd) to'ldiriladi; model rad etsa LLMRefusal ko'tariladi."""
        model = model or self.model
        reserved = self._begin(model, len(system) + len(user), max_tokens)
        try:
            with self.client.messages.stream(
                model=model, max_tokens=max_tokens, system=system,
                output_config={"effort": effort or "medium"},
                messages=[{"role": "user", "content": user}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
                final = stream.get_final_message()
            u = final.usage
            self._account(model, u)
        finally:
            self._end(reserved)
        self.last_stop_reason = final.stop_reason
        if meta is not None:
            price_in, price_out, _ = ANTHROPIC_PRICES.get(model, (0, 0, 0))
            meta.update(input_tokens=u.input_tokens, output_tokens=u.output_tokens, stop_reason=final.stop_reason,
                        cost_usd=(u.input_tokens * price_in + u.output_tokens * price_out) / 1_000_000)
        if final.stop_reason == "refusal":
            raise LLMRefusal(getattr(final.stop_details, "category", None))

    def cost_usd(self) -> float:
        """Shu jarayonda sarflangan jami dollar (har bir so'rov o'z modeli narxi bilan)."""
        return self.spent_usd

    def transcribe_image(self, image_bytes: bytes, mime_type: str = "image/jpeg",
                         system: str = "", prompt: str = "", timeout: int = 120,
                         max_tokens: int = 8192, model: str | None = None) -> tuple[str, float]:
        import base64
        b64_image = base64.b64encode(image_bytes).decode("ascii")
        prompt_text = prompt or "Ushbu hujjat tasviridagi barcha matnlarni 100% aslidagidek birga-bir ko'chirib ber."
        target_model = model or task_model("vision_ocr") or self.model
        reserved = self._begin(target_model, len(system) + len(prompt_text) + 2000, max_tokens)
        try:
            payload = {
                "model": target_model, "max_tokens": max_tokens, "temperature": 0.0,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64_image}},
                    {"type": "text", "text": prompt_text}
                ]}]
            }
            if system:
                payload["system"] = system
            resp = requests.post(f"{self.base_url}/v1/messages", timeout=timeout, headers={
                "x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"
            }, json=payload)
            resp.raise_for_status()
            data = resp.json()
        finally:
            self._end(reserved)
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage", {})
        cost = self._account(target_model, usage.get("input_tokens", 500), usage.get("output_tokens", len(text) // 2), 0)
        return text, cost

    def unload(self):
        pass



# 1 mln token narxi (input, output, cache read) — Gemini (Google AI Studio)
GEMINI_PRICES = {
    "gemini-3.1-flash-lite": (0.25, 1.50, 0.0),   # taxminiy (konservativ) narx — Google narxnomasi bilan solishtiring
    "gemini-flash-lite-latest": (0.075, 0.30, 0.0),
    "gemini-flash-latest": (0.075, 0.30, 0.0),
    "gemini-2.5-flash": (0.075, 0.30, 0.0),
    "gemini-2.5-flash-lite": (0.075, 0.30, 0.0),
    "gemini-2.5-pro": (1.25, 5.00, 0.0),
    "gemini-pro-latest": (1.25, 5.00, 0.0),
}


class GeminiProvider:
    name = "gemini"

    def __init__(self, model: str, api_key: str, base_url: str):
        if not api_key:
            raise ValueError(".env da GEMINI_API_KEY yo'q")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.usage = Usage()
        self.spent_usd = 0.0
        self.budget_usd = settings.LLM_BUDGET_USD  # 0 = cheklovsiz
        self.last_stop_reason = None
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._inflight = 0
        self._reserved_usd = 0.0

    def _clean_schema(self, s):
        """Gemini API qabul qilmaydigan additionalProperties va $schema ni tozalash."""
        if isinstance(s, dict):
            return {k: self._clean_schema(v) for k, v in s.items() if k not in ("additionalProperties", "$schema")}
        elif isinstance(s, list):
            return [self._clean_schema(item) for item in s]
        return s

    def _get_prices(self, model: str):
        return GEMINI_PRICES.get(model, (0.075, 0.30, 0.0))

    def _begin(self, model: str, prompt_chars: int, max_tokens: int) -> float:
        price_in, price_out, _ = self._get_prices(model)
        worst = (prompt_chars / 2 * price_in + max_tokens * price_out) / 1e6
        with self._cond:
            if self.budget_usd:
                while self._inflight and self.spent_usd + self._reserved_usd + worst > self.budget_usd:
                    self._cond.wait()
                if self.spent_usd >= self.budget_usd:
                    raise BudgetExceeded(f"Xarajat chegarasi tugadi: ${self.spent_usd:.4f} / ${self.budget_usd:.2f}")
            self._inflight += 1
            self._reserved_usd += worst
        return worst

    def extend_budget(self, amount: float) -> None:
        with self._cond:
            if self.budget_usd:
                self.budget_usd = max(self.budget_usd, self.spent_usd) + amount
            self._cond.notify_all()

    def _end(self, reserved: float) -> None:
        with self._cond:
            self._inflight -= 1
            self._reserved_usd -= reserved
            self._cond.notify_all()

    def _account(self, model: str, in_tok: int, out_tok: int) -> float:
        price_in, price_out, _ = self._get_prices(model)
        cost = (in_tok * price_in + out_tok * price_out) / 1e6
        with self._lock:
            self.usage.requests += 1
            self.usage.input_tokens += in_tok
            self.usage.output_tokens += out_tok
            self.spent_usd += cost
            try:
                with open(settings.DATA_DIR / "llm_usage.jsonl", "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "model": model,
                                         "in": in_tok, "out": out_tok, "cache_read": 0,
                                         "usd": round(cost, 6)}) + "\n")
            except Exception:
                pass
        return cost

    def _post_with_retry(self, url: str, payload: dict, timeout: int, stream: bool = False, model: str = ""):
        import time
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}  # kalit URL da emas: xato matniga tushmasin
        max_retries = 3
        current_url = url
        current_model = model

        for attempt in range(max_retries):
            try:
                resp = requests.post(current_url, json=payload, headers=headers, timeout=timeout, stream=stream)
                if resp.status_code == 200:
                    return resp, current_model
                if resp.status_code in (503, 429) and attempt < max_retries - 1:
                    if "flash-latest" in current_url:
                        current_url = current_url.replace("flash-latest", "flash-lite-latest")
                        current_model = "gemini-flash-lite-latest"
                    time.sleep(1.0 * (attempt + 1))
                    continue
                resp.raise_for_status()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                if attempt < max_retries - 1:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise
        raise RuntimeError(f"Gemini API javob bermadi ({current_model})")

    def chat_json(self, system: str, user: str, schema: dict | None = None, effort: str | None = None,
                  timeout: int = 300, max_tokens: int = 4096, model: str | None = None) -> dict:
        target_model = model or self.model
        url = f"{self.base_url}/v1beta/models/{target_model}:generateContent"

        gen_config = {
            "temperature": 0.0,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json"
        }
        if schema:
            gen_config["responseSchema"] = self._clean_schema(schema)

        payload = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen_config
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        reserved = self._begin(target_model, len(system) + len(user), max_tokens)
        try:
            resp, used_model = self._post_with_retry(url, payload, timeout=timeout, stream=False, model=target_model)
        finally:
            self._end(reserved)

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"Gemini bo'sh javob berdi: {data}")
        cand = candidates[0]
        self.last_stop_reason = cand.get("finishReason")
        if cand.get("finishReason") == "MAX_TOKENS":
            raise ValueError(f"Javob max_tokens={max_tokens} ga yetib kesildi")

        text = cand.get("content", {}).get("parts", [{}])[0].get("text", "{}")
        usage_meta = data.get("usageMetadata", {})
        in_tok = usage_meta.get("promptTokenCount", len(system + user) // 2)
        out_tok = usage_meta.get("candidatesTokenCount", len(text) // 2)
        self._account(used_model, in_tok, out_tok)

        return json.loads(text)

    def stream_text(self, system: str, user: str, effort: str | None = None, max_tokens: int = 16000,
                    meta: dict | None = None, model: str | None = None):
        target_model = model or self.model
        url = f"{self.base_url}/v1beta/models/{target_model}:streamGenerateContent?alt=sse"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_tokens
            }
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        reserved = self._begin(target_model, len(system) + len(user), max_tokens)
        try:
            resp, used_model = self._post_with_retry(url, payload, timeout=300, stream=True, model=target_model)
            total_in = 0
            total_out = 0
            full_text = []
            finish = None
            stray: list[str] = []   # "data:" bo'lmagan qatorlar — provayder xatosi (503 ...) shu yerda JSON bo'lib keladi
            failure: str | None = None

            try:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line_str = line.decode("utf-8")
                    if not line_str.startswith("data: "):
                        stray.append(line_str)
                        continue
                    try:
                        chunk_data = json.loads(line_str[6:])
                    except ValueError:
                        failure = "oqimda buzuq hodisa"
                        break
                    if isinstance(chunk_data.get("error"), dict):
                        failure = f"provayder xatosi: {chunk_data['error'].get('status') or chunk_data['error'].get('code')}"
                        break
                    cand = (chunk_data.get("candidates") or [{}])[0]
                    part_text = "".join(p.get("text", "") for p in (cand.get("content", {}).get("parts") or [])
                                        if not p.get("thought"))
                    if part_text:
                        full_text.append(part_text)
                        yield part_text
                    if "usageMetadata" in chunk_data:
                        u = chunk_data["usageMetadata"]
                        total_in = u.get("promptTokenCount", total_in)
                        total_out = u.get("candidatesTokenCount", total_out)
                    if cand.get("finishReason"):
                        finish = cand["finishReason"]
                        self.last_stop_reason = finish
            except (requests.exceptions.RequestException, OSError) as e:   # ulanish oqim o'rtasida uzildi
                failure = f"ulanish uzildi: {type(e).__name__}"
            if failure is None and "".join(stray).lstrip().startswith("{") and '"error"' in "".join(stray):
                failure = "provayder xatosi (oqim ichida)"   # xato JSON "data:" siz keladi (Gemini: 503 UNAVAILABLE)
            if failure is None and finish is None:
                failure = "oqim tugash belgisisiz yopildi"
            if failure is None and finish in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII") and not full_text:
                raise LLMRefusal(f"Gemini javob bermadi: {finish}")

            if not total_in:
                total_in = len(system + user) // 2
            if not total_out:
                total_out = len("".join(full_text)) // 2

            cost = self._account(used_model, total_in, total_out)   # uzilgan oqim ham pul turadi — hisobga olinadi
            if failure is not None:
                logger.warning("Gemini oqimi to'liq emas (%s): %d belgi olindi", failure, len("".join(full_text)))
                raise LLMInterrupted(failure)
            if meta is not None:
                meta.update(
                    input_tokens=total_in,
                    output_tokens=total_out,
                    stop_reason=self.last_stop_reason,
                    cost_usd=cost
                )
        finally:
            self._end(reserved)

    def transcribe_image(self, image_bytes: bytes, mime_type: str = "image/jpeg",
                         system: str = "", prompt: str = "", timeout: int = 120,
                         max_tokens: int = 8192, model: str | None = None) -> tuple[str, float]:
        """Tasvirdagi matnni multimodal Gemini orqali o'qiydi (Vision OCR).
        Qaytaradi: (aniqlangan_matn, xarajat_usd)."""
        import base64

        target_model = model or task_model("vision_ocr") or self.model
        url = f"{self.base_url}/v1beta/models/{target_model}:generateContent"

        b64_image = base64.b64encode(image_bytes).decode("ascii")
        prompt_text = prompt or "Ushbu hujjat tasviridagi barcha matnlarni 100% aslidagidek birga-bir ko'chirib ber."

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_image
                        }
                    },
                    {"text": prompt_text}
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": max_tokens
            }
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        reserved = self._begin(target_model, len(system) + len(prompt_text) + 2000, max_tokens)
        try:
            resp, used_model = self._post_with_retry(url, payload, timeout=timeout, stream=False, model=target_model)
        finally:
            self._end(reserved)

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"Gemini bo'sh javob berdi: {data}")
        cand = candidates[0]
        self.last_stop_reason = cand.get("finishReason")
        if cand.get("finishReason") == "MAX_TOKENS":
            raise ValueError(f"Javob max_tokens={max_tokens} ga yetib kesildi")

        text = "".join(p.get("text", "") for p in (cand.get("content", {}).get("parts") or []) if not p.get("thought"))
        usage_meta = data.get("usageMetadata", {})
        in_tok = usage_meta.get("promptTokenCount", 300)
        out_tok = usage_meta.get("candidatesTokenCount", len(text) // 2)
        cost = self._account(used_model, in_tok, out_tok)
        return text, cost

    def cost_usd(self) -> float:
        return self.spent_usd

    def unload(self):
        pass


def task_model(task: str) -> str | None:
    """Bosqich uchun model nomi (settings.LLM_TASK_MODELS). Ollama da None — lokal model ishlatiladi."""
    if settings.LLM_PROVIDER not in ("anthropic", "gemini"):
        return None
    return settings.LLM_TASK_MODELS.get(task, settings.LLM_MODEL)


@lru_cache(maxsize=1)
def get_llm():
    provider = settings.LLM_PROVIDER
    if provider == "ollama":
        return OllamaProvider(os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M"),
                              os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    if provider == "anthropic":
        return AnthropicProvider(settings.LLM_MODEL, settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_API_URL)
    if provider == "gemini":
        return GeminiProvider(settings.LLM_MODEL, settings.GEMINI_API_KEY, settings.GEMINI_API_URL)
    raise ValueError(f"Noma'lum LLM_PROVIDER: {provider}")
