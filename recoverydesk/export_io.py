"""Streaming writer with cancellation and strict partial-file cleanup."""
from __future__ import annotations
from typing import Iterable, Callable

CHUNK_SIZE = 1024 * 1024

class ExportCancelled(Exception):
    pass

def write_chunks(out, chunks: Iterable[bytes], *, cancel: Callable[[], bool] | None = None,
                 byte_progress: Callable[[int], None] | None = None) -> int:
    written = 0
    if cancel and cancel():
        raise ExportCancelled('Export abgebrochen.')
    for block in chunks:
        mv = memoryview(block)
        for start in range(0, len(mv), CHUNK_SIZE):
            if cancel and cancel():
                raise ExportCancelled('Export abgebrochen.')
            piece = mv[start:start + CHUNK_SIZE]
            while len(piece):
                count = out.write(piece)
                if count is None or count <= 0:
                    raise OSError('Unvollständiger Schreibvorgang auf dem Ziellaufwerk.')
                written += count
                if byte_progress:
                    byte_progress(count)
                piece = piece[count:]
    if cancel and cancel():
        raise ExportCancelled('Export abgebrochen.')
    return written
