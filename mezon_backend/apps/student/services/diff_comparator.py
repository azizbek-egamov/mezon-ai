"""Yuridik matnlar va qonun moddalarini qiyosiy taqqoslagich (ZERO API COST).
Python difflib orqali eski va yangi tahrirlar, shartnoma variantlari yoki qonun moddalaridagi
o'zgarishlarni so'zma-so'z, aniq taqqoslaydi.
"""
import difflib
import re


def compare_legal_texts(text_a: str, text_b: str) -> dict:
    """Ikki yuridik matnni taqqoslaydi.
    Qaytaradi:
      - similarity_ratio: o'xshashlik foizi (0.0 - 1.0)
      - stats: qo'shilgan, o'chirilgan, o'zgarmagan so'zlar soni
      - diff_segments: React da rangli ko'rsatish uchun segmentlar ro'yxati
    """
    text_a = text_a.strip()
    text_b = text_b.strip()

    if not text_a and not text_b:
        return {
            "similarity_ratio": 1.0,
            "stats": {"added": 0, "deleted": 0, "unchanged": 0},
            "diff_segments": [],
        }

    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    similarity = round(matcher.ratio(), 4)

    # So'zma-so'z tokenizatsiya
    words_a = re.findall(r"\S+|\s+", text_a)
    words_b = re.findall(r"\S+|\s+", text_b)

    sm = difflib.SequenceMatcher(None, words_a, words_b)
    segments = []
    added_count = 0
    deleted_count = 0
    unchanged_count = 0

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            chunk = "".join(words_a[i1:i2])
            unchanged_count += len([w for w in words_a[i1:i2] if w.strip()])
            segments.append({"type": "equal", "text": chunk})
        elif tag == "delete":
            chunk = "".join(words_a[i1:i2])
            deleted_count += len([w for w in words_a[i1:i2] if w.strip()])
            segments.append({"type": "delete", "text": chunk})
        elif tag == "insert":
            chunk = "".join(words_b[j1:j2])
            added_count += len([w for w in words_b[j1:j2] if w.strip()])
            segments.append({"type": "insert", "text": chunk})
        elif tag == "replace":
            chunk_del = "".join(words_a[i1:i2])
            chunk_ins = "".join(words_b[j1:j2])
            deleted_count += len([w for w in words_a[i1:i2] if w.strip()])
            added_count += len([w for w in words_b[j1:j2] if w.strip()])
            segments.append({"type": "delete", "text": chunk_del})
            segments.append({"type": "insert", "text": chunk_ins})

    return {
        "similarity_ratio": similarity,
        "stats": {
            "added_words": added_count,
            "deleted_words": deleted_count,
            "unchanged_words": unchanged_count,
        },
        "diff_segments": segments,
    }

