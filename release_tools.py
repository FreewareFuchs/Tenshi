"""Offline, standard-library-only release packaging and verification for Tenshi.

A portable archive contains just the Windows executable and public instructions;
it never copies user settings, diagnostic logs, source disk images or test data.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import sys
import zipfile

from recoverydesk import __version__

EXECUTABLE = 'Tenshi.exe'
PACKAGE_ITEMS = (EXECUTABLE, 'PORTABLE_START.txt', 'SHA256SUMS.sha256', 'LICENSE', 'THIRD_PARTY_NOTICES.txt')


def content_notices() -> bytes:
    root=Path(__file__).resolve().parent
    parts=[(root/'THIRD_PARTY_NOTICES.md').read_bytes().replace(b'\r\n',b'\n')]
    for path in sorted((root/'recoverydesk/assets/content_licenses').glob('*.txt')):
        parts.append(b'\n\n===== '+path.name.encode('utf-8')+b' =====\n\n'+path.read_bytes().replace(b'\r\n',b'\n'))
    return b'\n'.join(parts)

PORTABLE_TEXT = '''Tenshi {version} - Windows 10/11 (64-Bit), portable Ausgabe

1. Archiv in einen beliebigen Ordner entpacken.
2. Tenshi.exe starten. Keine Installation und keine Administratorrechte fuer
   die normale Ausfuehrung erforderlich; der Zugriff auf physische Laufwerke
   kann erhoehte Windows-Rechte voraussetzen.
3. Datenrettung nur auf ein anderes physisches Laufwerk exportieren.
   Zuerst an Test-Images ausprobieren.

WICHTIG: "Portable" bedeutet hier OHNE INSTALLER. Anzeigeeinstellungen und
Fehlerprotokolle werden weiterhin im Windows-Benutzerprofil gespeichert
(z. B. %%APPDATA%%\\Tenshi und %%LOCALAPPDATA%%\\Tenshi\\Logs).
Das Programm und seine Konfiguration sind NICHT komplett USB-portabel.

Der Quell-Datentraeger wird nur lesend verwendet. Auch eine scheinbar erfolgreich
wiederhergestellte Datei kann beschaedigt sein.
Dieses ZIP enthaelt keinerlei Original-Dateien, Datentraegerabbilder oder Logs.

Die Datei LICENSE enthaelt die MIT-Lizenz des Tenshi-Projekts.\nSHA256SUMS.sha256 nennt den SHA-256-Pruefwert der beigelegten Tenshi.exe.
Mit 'python release_tools.py verify <Pfad-zur-ZIP>' kann der Inhalt verifiziert werden.
'''


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _read_checked_exe(exe: Path) -> None:
    if exe.is_symlink() or not exe.is_file():
        raise ValueError('Es muss eine regulaere Tenshi.exe (kein Symlink) angegeben werden.')
    if exe.name.lower() != EXECUTABLE.lower():
        raise ValueError('Unerwarteter EXE-Name; erwartet wird Tenshi.exe.')
    if exe.stat().st_size < 1024:
        raise ValueError('Die EXE ist ungewoehnlich klein oder unvollstaendig.')
    with exe.open('rb') as stream:
        if stream.read(2) != b'MZ':
            raise ValueError('Die angegebene Datei ist keine Windows-PE-EXE (MZ fehlt).')


def create_portable(exe_path: str | Path, output_path: str | Path, *, overwrite: bool = False) -> Path:
    """Atomically make a deterministic-content ZIP, then validate its hashes."""
    raw_exe = Path(exe_path)
    if raw_exe.is_symlink():
        raise ValueError('Die angegebene EXE darf kein Symlink sein.')
    exe = raw_exe.resolve(strict=True)
    dest = Path(output_path).absolute()
    if dest.is_symlink():
        raise ValueError('Ausgabe darf kein Symlink sein.')
    if dest.exists() and not overwrite:
        raise FileExistsError(f'Ausgabe existiert bereits: {dest}')
    _read_checked_exe(exe)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_name(f'.{dest.name}.{secrets.token_hex(8)}.tmp')
    try:
        # Store the executable unchanged; compression is usually ineffective for
        # a PyInstaller onefile archive and would slow down ZIP generation.
        checksum_before = file_sha256(exe)
        with zipfile.ZipFile(temp, 'w') as archive:
            def put_bytes(name: str, content: bytes, compression: int) -> None:
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = compression
                info.external_attr = 0o100644 << 16
                archive.writestr(info, content)
            info = zipfile.ZipInfo(EXECUTABLE, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            with archive.open(info, 'w') as dst, exe.open('rb') as src:
                for chunk in iter(lambda: src.read(1024 * 1024), b''):
                    dst.write(chunk)
            put_bytes('PORTABLE_START.txt', PORTABLE_TEXT.format(version=__version__).encode('utf-8'), zipfile.ZIP_DEFLATED)
            put_bytes('SHA256SUMS.sha256', (checksum_before + '  ' + EXECUTABLE + '\n').encode('ascii'), zipfile.ZIP_DEFLATED)
            put_bytes('LICENSE', (Path(__file__).resolve().parent / 'LICENSE').read_bytes(), zipfile.ZIP_DEFLATED)
            put_bytes('THIRD_PARTY_NOTICES.txt', content_notices(), zipfile.ZIP_DEFLATED)
        if file_sha256(exe) != checksum_before:
            raise ValueError('Die EXE hat sich waehrend des Packens geaendert.')
        verify_portable(temp)
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)
    return dest


def verify_portable(path: str | Path) -> str:
    """Check archive names, checksums, PE header, and reject path injection."""
    with zipfile.ZipFile(path, 'r') as archive:
        names = archive.namelist()
        current=set(PACKAGE_ITEMS)
        historical=current-{'THIRD_PARTY_NOTICES.txt'}
        allowed=(current,historical,(current-{'SHA256SUMS.sha256'})|{'SHA256SUMS.txt'},
                 (historical-{'SHA256SUMS.sha256'})|{'SHA256SUMS.txt'})
        if len(names) != len(set(names)) or set(names) not in allowed:
            raise ValueError(f'ZIP muss ausschliesslich {PACKAGE_ITEMS} enthalten.')
        checksum = 'SHA256SUMS.sha256' if 'SHA256SUMS.sha256' in names else 'SHA256SUMS.txt'
        manifest = archive.read(checksum).decode('ascii')
        match = re.fullmatch(r'([a-f0-9]{64})  Tenshi\.exe\n', manifest)
        if not match:
            raise ValueError('Ungueltige SHA256-Pruefsummenliste.')
        exe_size = archive.getinfo(EXECUTABLE).file_size
        if exe_size < 1024:
            raise ValueError('Die EXE ist unvollstaendig.')
        digest = hashlib.sha256()
        with archive.open(EXECUTABLE, 'r') as stream:
            if stream.read(2) != b'MZ':
                raise ValueError('Ungueltiger Windows-EXE-Header.')
            digest.update(b'MZ')
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != match.group(1):
            raise ValueError('SHA-256-Pruefsumme der Tenshi.exe stimmt nicht.')
        # Git for Windows may check out LICENSE with CRLF. The actual MIT
        # license text must be valid regardless of the checkout line endings.
        license_text = archive.read('LICENSE').decode('utf-8').replace('\r\n', '\n')
        if not license_text.startswith('MIT License\n') or 'Copyright (c)' not in license_text:
            raise ValueError('MIT-Lizenzdatei im Portable-ZIP fehlt oder ist ungueltig.')
        if 'THIRD_PARTY_NOTICES.txt' in names and archive.read('THIRD_PARTY_NOTICES.txt').replace(b'\r\n',b'\n')!=content_notices():
            raise ValueError('Drittkomponenten-Lizenztexte im Portable-ZIP stimmen nicht.')
        info = archive.read('PORTABLE_START.txt').decode('utf-8')
        if f'Tenshi {__version__}' not in info:
            raise ValueError('Portabler Hinweis passt nicht zur Quellversion.')
        return match.group(1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Tenshi Windows-Portablepaket erstellen/pruefen')
    sub = parser.add_subparsers(dest='action', required=True)
    create = sub.add_parser('portable', help='Tenshi.exe in ein portables ZIP packen')
    create.add_argument('--exe', default='dist/Tenshi.exe')
    create.add_argument('--output', default=f'portable_output/Tenshi_Portable_{__version__}_Win64.zip')
    create.add_argument('--overwrite', action='store_true')
    check = sub.add_parser('verify', help='Portable-Archiv und SHA-256 verifizieren')
    check.add_argument('archive')
    args = parser.parse_args(argv)
    try:
        if args.action == 'portable':
            result = create_portable(args.exe, args.output, overwrite=args.overwrite)
            print('Portable Ausgabe erstellt:', result)
        else:
            digest = verify_portable(args.archive)
            print('Portable ZIP ist gueltig. SHA256(Tenshi.exe) =', digest)
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, UnicodeError) as exc:
        print(f'FEHLER: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
