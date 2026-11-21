import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import datetime
from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from django.test import SimpleTestCase

from apps.ops import backup


class BackupTests(SimpleTestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.data = self.root / "data"
        (self.data / "uploads").mkdir(parents=True)
        (self.data / "case_runs" / "sub").mkdir(parents=True)
        (self.data / "uploads" / "a.pdf.enc").write_bytes(b"shifrlangan-pdf" * 1000)
        (self.data / "case_runs" / "sub" / "r.json.enc").write_bytes(b"hisobot")
        (self.data / "lex_cache").mkdir()
        (self.data / "lex_cache" / "big.html").write_bytes(b"x")       # zaxiraga kirmaydi
        (self.data / "secret").mkdir()
        (self.data / "secret" / "data.key").write_bytes(b"kalit")       # kalit hech qachon arxivga kirmaydi
        self.db = self.data / "db.sqlite3"
        with closing(sqlite3.connect(self.db)) as con:
            con.execute("CREATE TABLE accounts_user (id INTEGER)")
            con.executemany("INSERT INTO accounts_user VALUES (?)", [(i,) for i in range(5)])
            con.commit()
        self.key = Fernet.generate_key().decode()
        self.dest = self.root / "backups"

    def make(self, **kw):
        kw.setdefault("now", datetime(2026, 10, 30, 3, 30))
        return backup.create_backup(self.dest, db_path=self.db, data_dir=self.data, keys=[self.key], **kw)

    def test_create_verify_restore(self):
        result = self.make()
        self.assertEqual(result.path.name, "mezon_20261030_033000.mzb")
        raw = result.path.read_bytes()
        self.assertTrue(raw.startswith(backup.MAGIC))
        self.assertNotIn(b"shifrlangan-pdf", raw)   # ichi shifrlangan
        self.assertNotIn(b"accounts_user", raw)
        self.assertEqual(list(self.dest.iterdir()), [result.path])  # vaqtinchalik fayllar qolmagan

        manifest = backup.verify_backup(result.path, [self.key])
        self.assertEqual(manifest["counts"], {"users": 5})
        self.assertEqual(set(manifest["files"]), {"db.sqlite3", "files/uploads/a.pdf.enc", "files/case_runs/sub/r.json.enc"})

        target = self.root / "restored"
        backup.restore_backup(result.path, target, [self.key])
        self.assertEqual((target / "files" / "uploads" / "a.pdf.enc").read_bytes(), b"shifrlangan-pdf" * 1000)
        with closing(sqlite3.connect(target / "db.sqlite3")) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM accounts_user").fetchone()[0], 5)
        self.assertFalse(any(p.name.startswith(".mezon_") for p in target.iterdir()))
        with self.assertRaisesMessage(backup.BackupError, "bo'sh emas"):
            backup.restore_backup(result.path, target, [self.key])

    def test_rotated_keys_and_wrong_key(self):
        path = self.make().path
        new = Fernet.generate_key().decode()
        backup.verify_backup(path, [new, self.key])  # kalit almashtirilgach ham eski zaxira ochiladi
        with self.assertRaisesMessage(backup.BackupError, "Kalit mos emas"):
            backup.verify_backup(path, [new])

    def test_tampering_and_truncation_detected(self):
        path = self.make().path
        raw = bytearray(path.read_bytes())
        raw[40] ^= 1
        path.with_name("buzilgan.mzb").write_bytes(raw)
        with self.assertRaisesMessage(backup.BackupError, "buzilgan"):
            backup.verify_backup(path.with_name("buzilgan.mzb"), [self.key])
        # oxirgi bo'lakni butunlay olib tashlash (chegarada kesish) ham aniqlanadi
        out = BytesIO()
        writer = backup.EncryptedWriter(out, backup.derive_key(self.key))
        writer.write(b"a" * (backup.CHUNK + 100))  # 1 to'liq bo'lak + oxirgi bo'lak
        writer.close()
        first_end = len(backup.MAGIC) + 8 + 5 + 12 + backup.CHUNK + 16  # sarlavha + bo'lak (tag 16 bayt)
        cut = path.with_name("kesilgan.mzb")
        cut.write_bytes(out.getvalue()[:first_end])
        with self.assertRaisesMessage(backup.BackupError, "kesilgan"):
            backup.decrypt_file(cut, BytesIO(), [self.key])

    def test_large_payload_spans_chunks(self):
        payload = os.urandom(backup.CHUNK * 2 + 1234)  # siqilmaydi — ZIP ichida ham bir necha bo'lak
        (self.data / "uploads" / "big.bin").write_bytes(payload)
        path = self.make().path
        plain = BytesIO()
        backup.decrypt_file(path, plain, [self.key])
        with zipfile.ZipFile(plain) as zf:
            self.assertEqual(zf.read("files/uploads/big.bin"), payload)
            self.assertIn("db.sqlite3", json.loads(zf.read("manifest.json"))["files"])

    def test_prune_keeps_newest(self):
        for day in range(1, 5):
            self.make(now=datetime(2026, 10, day, 3, 30), keep=2)
        self.assertEqual(sorted(p.name for p in self.dest.glob("*.mzb")),
                         ["mezon_20261003_033000.mzb", "mezon_20261004_033000.mzb"])

    def test_requires_key(self):
        with self.assertRaisesMessage(backup.BackupError, "MEZON_DATA_KEYS"):
            backup.create_backup(self.dest, db_path=self.db, data_dir=self.data, keys=[""])
