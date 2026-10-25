"""Optional, bounded ZIP structure/CRC check of a regular exported file.

Never extracts members or writes files. A passing CRC is not an original-file
comparison and does not validate Office/XML content inside ZIP containers.
"""
from dataclasses import dataclass
import os
import stat
import zipfile
import zlib

from .secure_target import open_regular_input

ZIP_CHECK_SCOPE = ('Prüft ZIP-Struktur und interne CRC-Prüfsummen. '
                   'Kein Vergleich mit dem Original und keine Prüfung des Inhaltsformats enthaltener Dateien.')
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 10000


@dataclass(frozen=True)
class ZipCheckResult:
    status: str
    files: int
    checked_bytes: int
    message: str


def verify_zip(path, *, cancel=None, max_archive_bytes=MAX_ARCHIVE_BYTES,
               max_expanded_bytes=MAX_EXPANDED_BYTES, max_members=MAX_MEMBERS):
    """Read ZIP members to EOF (including CRC validation), without extraction."""
    if min(max_archive_bytes, max_expanded_bytes, max_members) < 1:
        raise ValueError('ZIP check limits must be positive')
    files = count = 0
    def result(status, message):
        return ZipCheckResult(status, files, count, message)
    def cancelled():
        return bool(cancel and cancel())
    if cancelled():
        return result('cancelled', 'Prüfung abgebrochen.')
    try:
        # The helper anchors Linux opens and rejects special files/symlinks.
        # Independently check the opened handle on all supported platforms.
        with open_regular_input(os.fspath(path), os.fspath(path)) as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                return result('incomplete', 'Nur reguläre Dateien können geprüft werden.')
            if before.st_size > max_archive_bytes:
                return result('incomplete', 'ZIP-Prüfgrenze erreicht. Keine vollständige Prüfung.')
            with zipfile.ZipFile(stream) as archive:
                members = archive.infolist()
                if len(members) > max_members or sum(m.file_size for m in members) > max_expanded_bytes:
                    return result('incomplete', 'ZIP-Prüfgrenze erreicht. Keine vollständige Prüfung.')
                for member in members:
                    if cancelled():
                        return result('cancelled', 'Prüfung abgebrochen.')
                    if member.flag_bits & 1:
                        return result('incomplete', 'Verschlüsselte ZIP-Inhalte werden nicht geprüft.')
                    with archive.open(member) as content:
                        while True:
                            if cancelled():
                                return result('cancelled', 'Prüfung abgebrochen.')
                            block = content.read(64 * 1024)
                            if not block:
                                break
                            count += len(block)
                            if count > max_expanded_bytes:
                                return result('incomplete', 'ZIP-Prüfgrenze erreicht. Keine vollständige Prüfung.')
                    if not member.is_dir():
                        files += 1
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                return result('incomplete', 'Datei während der Prüfung geändert. Keine Bestätigung möglich.')
        if cancelled():
            return result('cancelled', 'Prüfung abgebrochen.')
        return result('passed', 'ZIP-Struktur und CRC-Prüfsummen ohne Fehler geprüft.')
    except (zipfile.BadZipFile, EOFError, zlib.error):
        return result('failed', 'ZIP beschädigt, unvollständig oder kein unterstütztes ZIP-Archiv.')
    except (NotImplementedError, RuntimeError):
        return result('incomplete', 'ZIP-Kompression wird nicht unterstützt. Keine vollständige Prüfung.')
    except (OSError, ValueError):
        return result('incomplete', 'Datei konnte nicht vollständig gelesen werden.')
