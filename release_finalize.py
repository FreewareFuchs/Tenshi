"""Local, stdlib-only release check/copy step for Tenshi 3.0.2.

Builds nothing and uploads nothing. It will not create a misleading release if a
Windows binary is missing, not a PE file, or the portable ZIP fails verification.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from release_tools import verify_portable, file_sha256
from open_source_preflight import check as mit_preflight

VERSION = "3.0.2"
BASE = Path(__file__).resolve().parent
OUT = BASE / "VEROEFFENTLICHUNG" / "UPLOAD"
ENTRIES = {
    f"Tenshi_Setup_{VERSION}.exe": BASE / "installer_output" / f"Tenshi_Setup_{VERSION}.exe",
    f"Tenshi_Portable_{VERSION}_Win64.zip": BASE / "portable_output" / f"Tenshi_Portable_{VERSION}_Win64.zip",
}

def check_pe(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size < 1024:
        raise ValueError(f"Fehlende oder ungueltige Windows-Datei: {path}")
    with path.open("rb") as f:
        if f.read(2) != b"MZ":
            raise ValueError(f"Kein Windows-PE-Dateianfang: {path}")

def main() -> int:
    release_errors = mit_preflight()
    if release_errors:
        raise ValueError("MIT-Freigabe gesperrt: " + "; ".join(release_errors))
    exe = BASE / "dist" / "Tenshi.exe"
    check_pe(exe)
    check_pe(ENTRIES[f"Tenshi_Setup_{VERSION}.exe"])
    digest_exe = file_sha256(exe)
    digest_zip_exe = verify_portable(ENTRIES[f"Tenshi_Portable_{VERSION}_Win64.zip"])
    if digest_exe != digest_zip_exe:
        raise ValueError("Portable-EXE ist nicht identisch zum Release-Build (SHA256).")
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"product": "Tenshi", "version": VERSION, "channel": "beta",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "notice": "MIT-Lizenz: Rechte an Assets, Drittkomponenten und Website vor Veroeffentlichung pruefen.",
              "artifacts": []}
    lines = []
    for name, source in ENTRIES.items():
        dst = OUT / name
        if dst.is_symlink():
            raise ValueError(f"Upload-Ziel darf kein Symlink sein: {dst}")
        shutil.copy2(source, dst)
        digest = file_sha256(dst)
        if digest != file_sha256(source):
            raise ValueError(f"Kopierfehler: {name}")
        result["artifacts"].append({"file": name, "sha256": digest, "bytes": dst.stat().st_size})
        lines.append(f"{digest}  {name}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
    (OUT / "release_manifest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "VOR_UPLOAD_LESEN.txt").write_text(
        "Tenshi 3.0.2 Beta (MIT): Rechteinhaber und Drittkomponenten, Impressum, "
        "Datenschutz, Code-Signierung und finalen Windows-Test vor "
        "Veroeffentlichung pruefen. SHA256SUMS.txt nur fuer diese zwei "
        "unveraenderten Pakete verwenden.\n", encoding="utf-8")
    print("Gepruefte Release-Artefakte in:", OUT)
    for row in result["artifacts"]:
        print(row["file"], row["bytes"], "Bytes; SHA256", row["sha256"])
    print("WICHTIG: Rechtliche Freigabe und letzten Windows-Test separat erledigen!")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print("RELEASE-FEHLER:", exc, file=sys.stderr)
        raise SystemExit(2)
