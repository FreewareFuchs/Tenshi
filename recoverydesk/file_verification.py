"""Bounded, read-only file readability verification.

The calculated SHA-256 identifies the bytes just read, NOT a known-good copy.
It cannot establish authenticity or whether deleted clusters were overwritten.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
from typing import Callable

from .ntfs import iter_stream
from .sources import open_source

MAX_VERIFY_BYTES = 512 * 1024 * 1024
ZERO_BLOCK = bytes(1024 * 1024)

class VerificationCancelled(Exception):
    pass

class VerificationError(Exception):
    pass

@dataclass(frozen=True)
class VerificationResult:
    expected_bytes: int
    read_bytes: int
    sha256: str
    complete: bool
    message: str


def verify_file(source: str, index, entry, *, filesystem: str,
                max_bytes: int = MAX_VERIFY_BYTES,
                cancel: Callable[[], bool] | None = None,
                progress: Callable[[int], None] | None = None) -> VerificationResult:
    """Read the selected file and compare streamed byte count with metadata size.

    Never writes to source or destination. Limits total read and peak memory.
    """
    if entry.is_directory or not entry.recoverable:
        raise VerificationError('Dieser Eintrag hat keinen unterstützten lesbaren Dateidatenstrom.')
    size = entry.size
    if not isinstance(size, int) or size < 0:
        raise VerificationError('Unplausible Dateigröße.')
    if max_bytes <= 0 or size > max_bytes:
        raise VerificationError(f'Die Datei ist für die Leseprüfung zu groß (Grenze: {max_bytes:,} Bytes).')

    digest = hashlib.sha256()
    count = 0
    def take(chunks):
        nonlocal count
        for block in chunks:
            if cancel and cancel():
                raise VerificationCancelled('Leseprüfung abgebrochen.')
            if not isinstance(block, (bytes, bytearray, memoryview)):
                raise VerificationError('Dateistream hat keine Byte-Daten geliefert.')
            if len(block) > max_bytes - count or count + len(block) > size:
                raise VerificationError('Datenstrom überschreitet die gemeldete Dateigröße.')
            digest.update(block)
            count += len(block)
            if progress:
                progress(count)

    if cancel and cancel():
        raise VerificationCancelled('Leseprüfung abgebrochen.')
    with open_source(source) as f:
        if filesystem == 'NTFS':
            if entry.data_kind == 'resident':
                resident = entry.resident_data
                if resident is None or len(resident) != size:
                    raise VerificationError('Inkonsistenter residenter NTFS-Datenstrom.')
                take([resident])
            elif entry.data_kind == 'nonresident':
                initialized = entry.initialized_size
                if not 0 <= initialized <= size:
                    raise VerificationError('Ungültige NTFS-Größe des initialisierten Datenbereichs.')
                take(iter_stream(f, index.info, entry.data_runs, 0, initialized))
                remaining = size - initialized
                while remaining:
                    step = min(remaining, len(ZERO_BLOCK))
                    take((memoryview(ZERO_BLOCK)[:step],))
                    remaining -= step
            else:
                raise VerificationError('Nicht unterstützter NTFS-Datenstrom.')
        else:
            # All generic readers implement iter_file(). Their metadata-driven
            # cluster resolution remains the source of truth for the byte stream.
            take(index.volumes.iter_file(f, entry, max_bytes=size))
    if cancel and cancel():
        raise VerificationCancelled('Leseprüfung abgebrochen.')
    if count != size:
        raise VerificationError(f'Datenstrom unvollständig: {count:,} von {size:,} Bytes lesbar.')
    return VerificationResult(size, count, digest.hexdigest(), True,
        'Die gemeldete Dateigröße wurde vollständig gelesen. '\
        'Die SHA-256-Prüfsumme beschreibt nur die aktuell lesbaren Bytes. '\
        'Sie beweist weder die ursprüngliche Integrität noch die Rettbarkeit gelöschter Daten.')
