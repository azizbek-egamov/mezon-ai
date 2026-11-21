"""Android release imzo kaliti (bir marta): credentials/release.keystore + credentials/release.properties.

    python apps/mobile/scripts/create-keystore.py

Parol tasodifiy, faqat properties fayliga yoziladi (ekranga chiqmaydi). credentials/ git ga kirmaydi.
MUHIM: ikkala faylni zaxiralang (parol menejeri / tashqi disk) — kalit yo'qolsa, o'rnatilgan ilovani yangilab
bo'lmaydi (faqat o'chirib, qayta o'rnatish).
"""
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
CRED = APP / "credentials"
STORE = CRED / "release.keystore"
PROPS = CRED / "release.properties"
ALIAS = "mezon"


def keytool() -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home and (Path(java_home) / "bin" / "keytool.exe").exists():
        return str(Path(java_home) / "bin" / "keytool.exe")
    found = shutil.which("keytool")
    if not found:
        sys.exit("keytool topilmadi: JAVA_HOME (JDK 17) ni sozlang")
    return found


def main() -> None:
    if STORE.exists() or PROPS.exists():
        sys.exit(f"Kalit allaqachon bor: {CRED} — qayta yaratilmaydi (eski ilova yangilanmay qoladi)")
    CRED.mkdir(exist_ok=True)
    password = secrets.token_urlsafe(24)
    subprocess.run(
        [keytool(), "-genkeypair", "-storetype", "PKCS12", "-keystore", str(STORE), "-alias", ALIAS,
         "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000", "-storepass", password, "-keypass", password,
         "-dname", "CN=MEZON AI, O=MEZON, C=UZ"],
        check=True, capture_output=True)
    PROPS.write_text(
        "# MEZON Android release imzosi (git ga kirmaydi). Zaxiralang!\n"
        f"storeFile=release.keystore\nkeyAlias={ALIAS}\nstorePassword={password}\nkeyPassword={password}\n",
        encoding="utf-8")
    print(f"Yaratildi: {STORE.name}, {PROPS.name} ({CRED}). Ikkalasini zaxiralang.")


if __name__ == "__main__":
    main()
