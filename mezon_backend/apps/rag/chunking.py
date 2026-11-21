"""Matn birliklarini (modda/band) qidiruv bo'laklariga ajratish.

Bo'lak = modda (yoki band) yoki, uzun bo'lsa, ketma-ket qismlar guruhi. Har bir bo'lak matni
oldiga kontekst qo'shiladi: "<hujjat nomi> | <bob> | 168-modda. Firibgarlik" — embedding va
reranker moddani qaysi hujjatga tegishli ekanini "ko'rishi" uchun.

Til: `lang=None` — moddaning asosiy (yuklangan) tili; 'lat' | 'cyr' | 'ru' — shu tildagi versiya (TZ §5.4).
Asosiy til bo'laklarining id si tilsiz formada qoladi (indeksdagi mavjud nuqtalar o'zgarmaydi).
"""
import uuid
from dataclasses import dataclass, field
from typing import Callable

from apps.lex_corpus.models import LegalActArticle

CHUNK_NAMESPACE = uuid.UUID("6c1f3a52-8a4e-4c0e-9a51-6d3b2f1e7a10")


@dataclass
class Chunk:
    chunk_id: str
    article_id: int
    header: str
    body: str
    part_numbers: list[int]
    elem_ids: list[str]
    payload: dict = field(default_factory=dict)
    lang: str = ""        # bo'lak tili ('lat' | 'cyr' | 'ru')
    index: int = 0        # moddadagi bo'lak tartibi (tillar orasida taqqoslash uchun)

    @property
    def text(self) -> str:
        return f"{self.header}\n{self.body}"


def unit_label(article: LegalActArticle, lang: str | None = None) -> str:
    if lang is not None:
        return article.lang_label(lang)
    if article.unit_type == "ARTICLE":
        return f"{article.article_number}-modda. {article.heading}".strip()
    if article.unit_type == "BAND":
        return f"{article.article_number}-band"
    if article.unit_type == "PREAMBLE":
        return "Kirish qismi"
    return ""


def article_header(article: LegalActArticle, doc_title: str, lang: str | None = None) -> str:
    path = article.section_path if lang is None else article.section_in(lang)
    section = path.split(" / ")[-1] if path else ""
    return " | ".join(x for x in [doc_title, section, unit_label(article, lang)] if x)


def _parts(article: LegalActArticle, lang: str | None) -> list[dict]:
    if lang is None:
        return article.parts or [{"n": 1, "elem_ids": [article.lex_elem_id], "text": article.primary_text}]
    return article.parts_in(lang) or [{"n": 1, "elem_ids": [article.elem_id_in(lang)], "text": article.text_in(lang)}]


def split_article(article: LegalActArticle, doc_title: str, count_tokens: Callable[[str], int],
                  max_tokens: int, lang: str | None = None) -> list[Chunk]:
    header = article_header(article, doc_title, lang)
    parts = _parts(article, lang)
    budget = max(64, max_tokens - count_tokens(header))
    source = lang is None or lang == article.source_lang
    lang = article.source_lang if lang is None else lang

    # Qismlarni ketma-ket guruhlaymiz; bitta qism byudjetdan katta bo'lsa — abzaslar bo'yicha bo'linadi.
    pieces: list[tuple[list[int], list[str], str]] = []
    for p in parts:
        if count_tokens(p["text"]) <= budget:
            pieces.append(([p["n"]], list(p["elem_ids"]), p["text"]))
            continue
        paragraphs = p["text"].split("\n")
        ids = list(p["elem_ids"])
        for i, para in enumerate(paragraphs):
            pieces.append(([p["n"]], [ids[i]] if i < len(ids) else [], para))

    groups: list[tuple[list[int], list[str], list[str]]] = []
    used = 0
    for nums, ids, text in pieces:
        t = count_tokens(text)
        if groups and used + t <= budget:
            g = groups[-1]
            g[0].extend(n for n in nums if n not in g[0])
            g[1].extend(ids)
            g[2].append(text)
            used += t
        else:
            groups.append((list(nums), list(ids), [text]))
            used = t

    chunks = []
    for k, (nums, ids, texts) in enumerate(groups):
        key = f"{article.pk}:{k}" if source else f"{article.pk}:{lang}:{k}"
        chunks.append(Chunk(chunk_id=str(uuid.uuid5(CHUNK_NAMESPACE, key)), article_id=article.pk, header=header,
                            body="\n".join(texts), part_numbers=nums, elem_ids=ids, lang=lang, index=k))
    return chunks
