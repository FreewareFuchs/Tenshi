"""Small, bounded preview classifier; no RAW hex editor or signature search."""
from __future__ import annotations
from dataclasses import dataclass

PREVIEW_LIMIT = 128 * 1024
IMAGE_LIMIT = 2 * 1024 * 1024

@dataclass(frozen=True)
class Preview:
    kind: str  # text, image, binary, empty
    text: str
    image_format: str = ''

def describe(data: bytes, file_size: int) -> Preview:
    if not data:
        return Preview('empty', 'Die Datei ist leer.' if file_size == 0 else 'Keine Daten lesbar.')
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return Preview('image', 'PNG-Bildvorschau', 'png')
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return Preview('image', 'GIF-Bildvorschau', 'gif')
    if data.startswith(b'%PDF-'):
        return Preview('binary', 'PDF-Dokument: Keine integrierte PDF-Darstellung. Datei exportieren und in einem geeigneten Programm prüfen.')
    if data.startswith(b'PK\x03\x04'):
        return Preview('binary', 'ZIP-/Office-Archiv: Keine direkte Inhaltsvorschau. Datei exportieren und prüfen.')
    if data.startswith((b'\xff\xd8\xff', b'BM')):
        return Preview('binary', 'Bilddatei: Für dieses Format ist keine integrierte Bilddarstellung verfügbar.')
    bom = None
    if data.startswith(b'\xff\xfe'):
        bom = 'utf-16'
    elif data.startswith(b'\xfe\xff'):
        bom = 'utf-16'
    elif data.startswith(b'\xef\xbb\xbf'):
        bom = 'utf-8-sig'
    # Strings with many NUL bytes are not presumed to be UTF-8 text.
    if bom is None and b'\x00' in data:
        return Preview('binary', 'Binärdatei: keine sichere Textvorschau verfügbar.')
    try:
        decoded = data.decode(bom or 'utf-8', errors='strict')
    except UnicodeDecodeError:
        return Preview('binary', 'Binärdatei oder nicht unterstützte Textkodierung.')
    allowed = sum(ch.isprintable() or ch in '\r\n\t' for ch in decoded)
    if decoded and allowed / len(decoded) >= 0.92:
        suffix = '\n\n[Die Vorschau ist begrenzt; dies ist nicht die vollständige Datei.]' if file_size > len(data) else ''
        return Preview('text', decoded + suffix)
    return Preview('binary', 'Binärdaten: Vorschau auf lesbaren Text beschränkt.')
