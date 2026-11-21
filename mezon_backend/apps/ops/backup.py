"""Zaxira nusxa: baza + ish fayllari (+ ixtiyoriy Qdrant snapshot) -> bitta shifrlangan `.mzb` fayl.

Nima uchun shifrlangan: arxivda butun baza (telefonlar, ish faktlari, hisobotlar) bor va u boshqa diskka/bulutga
ko'chiriladi. Kalit — MEZON_DATA_KEYS (birinchisi) dan HKDF bilan hosil qilinadi; **kalitning o'zi arxivga
kirmaydi** — uni alohida (parol menejerida) saqlang, aks holda zaxira ochilmaydi.

Format (`MEZONBK1`): MAGIC(8) | kalit_id(8) | bo'laklar…; bo'lak = oxirgimi(1) | uzunlik(4) | nonce(12) | AES-GCM
shifrmatn. AAD = (tartib raqami, oxirgimi) — bo'laklarni almashtirish, olib tashlash yoki kesib qo'yish aniqlanadi.
Ichida oddiy ZIP: db.sqlite3, files/…, qdrant/… va manifest.json (har faylning SHA-256 si).
Shifrlanmagan ZIP diskka yozilmaydi (to'g'ridan-to'g'ri shifrlovchi oqimga); bazaning vaqtinchalik nusxasi
(SQLite online backup) manzil papkasida yaratiladi va darhol o'chiriladi.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import sqlite3
import struct
import tempfile
import zipfile
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

MAGIC = b"MEZONBK1"
CHUNK = 1 << 20  # 1 MB
SUFFIX = ".mzb"
NAME_PREFIX = "mezon_"
FILE_DIRS = ("uploads", "case_runs")       # DATA_DIR ichidagi foydalanuvchi fayllari (shifrlangan PDF/hisobotlar)
EXTRA_FILES = ("llm_usage.jsonl",)          # AI xarajatlari jurnali


class BackupError(Exception):
    pass


# --- shifrlash ---------------------------------------------------------------------------------------------------

def derive_key(fernet_key: str) -> bytes:
    raw = base64.urlsafe_b64decode(fernet_key.strip().encode())
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"mezon-backup-v1").derive(raw)


def key_id(key: bytes) -> bytes:
    return hashlib.sha256(b"mezon-backup-key-id" + key).digest()[:8]


def _aad(index: int, last: bool) -> bytes:
    return struct.pack(">Q?", index, last)


class EncryptedWriter(io.RawIOBase):
    """Yozilganni 1 MB lik bo'laklarda shifrlab `fh` ga yozadi. zipfile uchun (seek siz) oqim."""

    def __init__(self, fh, key: bytes):
        super().__init__()
        self._fh, self._aes, self._buf, self._index = fh, AESGCM(key), bytearray(), 0
        fh.write(MAGIC + key_id(key))

    def writable(self) -> bool:
        return True

    def write(self, data) -> int:
        self._buf += data
        while len(self._buf) >= CHUNK:
            self._emit(bytes(self._buf[:CHUNK]), last=False)
            del self._buf[:CHUNK]
        return len(data)

    def _emit(self, data: bytes, last: bool) -> None:
        nonce = os.urandom(12)
        ct = self._aes.encrypt(nonce, data, _aad(self._index, last))
        self._fh.write(struct.pack(">?I", last, len(ct)) + nonce + ct)
        self._index += 1

    def close(self) -> None:
        if not self.closed:
            self._emit(bytes(self._buf), last=True)  # oxirgi (bo'sh bo'lishi mumkin) bo'lak — kesilishdan himoya
            self._buf.clear()
        super().close()


def decrypt_file(src: Path, dst, keys: list[str]) -> None:
    """`.mzb` ni ochib `dst` (yozish uchun ochilgan fayl) ga ZIP ni yozadi. Kalit mos kelmasa yoki fayl
    o'zgartirilgan/kesilgan bo'lsa — BackupError."""
    with open(src, "rb") as fh:
        if fh.read(len(MAGIC)) != MAGIC:
            raise BackupError("Bu MEZON zaxira fayli emas.")
        kid = fh.read(8)
        key = next((k for k in (derive_key(x) for x in keys if x.strip()) if key_id(k) == kid), None)
        if key is None:
            raise BackupError("Kalit mos emas: zaxira boshqa MEZON_DATA_KEYS bilan yaratilgan.")
        aes, index = AESGCM(key), 0
        while True:
            head = fh.read(5)
            if len(head) < 5:
                raise BackupError("Zaxira fayli kesilgan (oxirgi bo'lak yo'q).")
            last, size = struct.unpack(">?I", head)
            nonce, ct = fh.read(12), fh.read(size)
            if len(ct) < size:
                raise BackupError("Zaxira fayli kesilgan.")
            try:
                dst.write(aes.decrypt(nonce, ct, _aad(index, last)))
            except InvalidTag:
                raise BackupError("Zaxira fayli buzilgan yoki o'zgartirilgan.") from None
            index += 1
            if last:
                if fh.read(1):
                    raise BackupError("Zaxira faylining oxirida ortiqcha ma'lumot bor.")
                return


# --- yaratish ----------------------------------------------------------------------------------------------------

@dataclass
class BackupResult:
    path: Path
    size: int
    entries: int
    removed: list[Path] = field(default_factory=list)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _counts(db: Path) -> dict:
    out = {}
    with closing(sqlite3.connect(db)) as con:  # Windows: fayl qulfi yopilsin
        for name, table in (("users", "accounts_user"), ("cases", "cases_caserun"), ("articles", "lex_corpus_legalactarticle")):
            try:
                out[name] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                pass  # jadval yo'q (masalan, testdagi kichik baza)
    return out


def _sqlite_copy(src: Path, dst: Path) -> None:
    """Ishlab turgan bazaning izchil nusxasi (SQLite online backup API: yozuvlar to'xtatilmaydi)."""
    source = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
    finally:  # Windows: fayl qulfi yopilsin
        source.close()
        target.close()
    with closing(sqlite3.connect(dst)) as con:  # Windows: fayl qulfi yopilsin
        status = con.execute("PRAGMA quick_check").fetchone()[0]
    if status != "ok":
        raise BackupError(f"Baza nusxasi tekshiruvdan o'tmadi: {status}")


def _qdrant_snapshot(url: str, collection: str, zf: zipfile.ZipFile, manifest: dict) -> None:
    base = f"{url.rstrip('/')}/collections/{collection}/snapshots"
    r = requests.post(base, params={"wait": "true"}, timeout=3600)
    r.raise_for_status()
    name = r.json()["result"]["name"]
    try:
        h = hashlib.sha256()
        with requests.get(f"{base}/{name}", stream=True, timeout=3600) as resp:
            resp.raise_for_status()
            # snapshot o'zi siqilgan arxiv — qayta siqilmaydi
            with zf.open(f"qdrant/{name}", "w", force_zip64=True) as out:
                for block in resp.iter_content(CHUNK):
                    h.update(block)
                    out.write(block)
        manifest["files"][f"qdrant/{name}"] = h.hexdigest()
        manifest["qdrant"] = {"collection": collection, "snapshot": name}
    finally:
        requests.delete(f"{base}/{name}", timeout=60)  # serverda snapshot qolib ketmasin (joy)


def create_backup(dest: Path, *, db_path: Path, data_dir: Path, keys: list[str], keep: int = 7,
                  qdrant_url: str = "", qdrant_collection: str = "", now: datetime | None = None) -> BackupResult:
    keys = [k for k in keys if k.strip()]
    if not keys:
        raise BackupError("MEZON_DATA_KEYS bo'sh — zaxira shifrlanmaydi, demak yaratilmaydi.")
    dest.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    final = dest / f"{NAME_PREFIX}{stamp}{SUFFIX}"
    partial = final.with_name(final.name + ".part")
    tmp = Path(tempfile.mkdtemp(prefix=".mezon_tmp_", dir=dest))
    manifest: dict = {"format": 1, "created": (now or datetime.now()).isoformat(timespec="seconds"), "files": {}}
    try:
        db_copy = tmp / "db.sqlite3"
        _sqlite_copy(db_path, db_copy)
        manifest["counts"] = _counts(db_copy)
        with open(partial, "wb") as raw, EncryptedWriter(raw, derive_key(keys[0])) as enc, \
                zipfile.ZipFile(enc, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.write(db_copy, "db.sqlite3")
            manifest["files"]["db.sqlite3"] = _sha256(db_copy)
            db_copy.unlink()  # shifrlanmagan nusxa iloji boricha qisqa vaqt yashasin
            for sub in FILE_DIRS:
                for path in sorted((data_dir / sub).rglob("*")) if (data_dir / sub).is_dir() else []:
                    if path.is_file():
                        arc = f"files/{sub}/{path.relative_to(data_dir / sub).as_posix()}"
                        zf.write(path, arc)
                        manifest["files"][arc] = _sha256(path)
            for name in EXTRA_FILES:
                if (data_dir / name).is_file():
                    zf.write(data_dir / name, f"files/{name}")
                    manifest["files"][f"files/{name}"] = _sha256(data_dir / name)
            if qdrant_url:
                _qdrant_snapshot(qdrant_url, qdrant_collection, zf, manifest)
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
        os.replace(partial, final)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        partial.unlink(missing_ok=True)
    removed = prune(dest, keep)
    return BackupResult(final, final.stat().st_size, len(manifest["files"]), removed)


def prune(dest: Path, keep: int) -> list[Path]:
    """Eng yangi `keep` ta zaxirani qoldiradi (disk to'lmasin). keep <= 0 — hech narsa o'chirilmaydi."""
    if keep <= 0:
        return []
    old = sorted(dest.glob(f"{NAME_PREFIX}*{SUFFIX}"), reverse=True)[keep:]
    for path in old:
        path.unlink()
    return old


# --- tekshirish va tiklash ---------------------------------------------------------------------------------------

def _open_zip(path: Path, keys: list[str], workdir: Path) -> zipfile.ZipFile:
    plain = workdir / "backup.zip"
    with open(plain, "wb") as out:
        decrypt_file(path, out, keys)
    return zipfile.ZipFile(plain)


def _check(zf: zipfile.ZipFile, workdir: Path) -> dict:
    manifest = json.loads(zf.read("manifest.json"))
    for arc, digest in manifest["files"].items():
        h = hashlib.sha256()
        with zf.open(arc) as f:
            for block in iter(lambda: f.read(CHUNK), b""):
                h.update(block)
        if h.hexdigest() != digest:
            raise BackupError(f"Nazorat yig'indisi mos emas: {arc}")
    db = Path(zf.extract("db.sqlite3", workdir))
    with closing(sqlite3.connect(db)) as con:  # Windows: fayl qulfi yopilsin
        status = con.execute("PRAGMA quick_check").fetchone()[0]
    if status != "ok":
        raise BackupError(f"Zaxiradagi baza buzilgan: {status}")
    if _counts(db) != manifest.get("counts", {}):
        raise BackupError("Zaxiradagi baza manifestga mos emas.")
    return manifest


def verify_backup(path: Path, keys: list[str]) -> dict:
    """Ochadi, har faylning SHA-256 sini va bazani (quick_check) tekshiradi. Natija — manifest."""
    work = Path(tempfile.mkdtemp(prefix=".mezon_verify_", dir=path.parent))
    try:
        with _open_zip(path, keys, work) as zf:
            return _check(zf, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def restore_backup(path: Path, target: Path, keys: list[str]) -> dict:
    """Zaxirani YANGI papkaga ochadi (ishlab turgan data/ ga tegmaydi): db.sqlite3, files/, qdrant/, manifest.json.
    Almashtirish — qo'lda, server to'xtatilgach (README: "Zaxira nusxa")."""
    if target.exists() and any(target.iterdir()):
        raise BackupError(f"Papka bo'sh emas: {target}")
    target.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=".mezon_restore_", dir=target))
    try:
        with _open_zip(path, keys, work) as zf:
            manifest = _check(zf, work)
            zf.extractall(target)  # zipfile nomlarni tozalaydi (../ yo'q)
        return manifest
    finally:
        shutil.rmtree(work, ignore_errors=True)
