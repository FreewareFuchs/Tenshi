"""Non-invasive Windows preflight for Tenshi.

Never opens, enumerates, mounts or writes to any source drive. The generated
report contains no user paths, device serials, disk contents or filenames.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import struct
import sys
import tempfile

from recoverydesk import __version__


def _admin_status() -> bool | None:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError, ValueError):
        return None


def _temporary_file_check() -> bool:
    """Only create an ordinary temporary file; never open a source device."""
    try:
        with tempfile.TemporaryFile(mode='w+b') as stream:
            stream.write(b'Tenshi preflight')
            stream.flush()
            stream.seek(0)
            return stream.read() == b'Tenshi preflight'
    except OSError:
        return False


def gather_report() -> dict:
    windows = platform.system() == 'Windows'
    bits = struct.calcsize('P') * 8
    writable = _temporary_file_check()
    checks = {
        'windows': windows,
        'python_64bit': bits == 64,
        'python_supported': sys.version_info >= (3, 11),
        'temporary_files_available': writable,
    }
    return {
        'tenshi_version': __version__,
        'purpose': 'Windows-Vorabpruefung ohne Zugriff auf Quelldatentraeger',
        'checks': checks,
        'passed': all(checks.values()),
        'administrator': _admin_status() if windows else None,
        'usb_source_tested': False,
        'raw_disk_access_tested': False,
        'installer_tested': False,
        'notice': ('Dieser Bericht testet KEINE echten Datentraeger. Fuer direkte '
                   'Laufwerkszugriffe koennen Administratorrechte erforderlich sein. '
                   'Beschadigte Datentraeger zuerst schonend sichern.'),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Tenshi Windows-Vorabpruefung (nur PC/Dateisystem TEMP)')
    parser.add_argument('--output', help='Optionaler Speicherort der JSON-Ergebnisse')
    args = parser.parse_args(argv)
    report = gather_report()
    data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    print(data, end='')
    if args.output:
        try:
            # Never overwrite an existing report without explicit deletion.
            with open(args.output, 'x', encoding='utf-8') as f:
                f.write(data)
        except OSError as exc:
            print('Bericht konnte nicht gespeichert werden:', type(exc).__name__, file=sys.stderr)
            return 1
    return 0 if report['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
