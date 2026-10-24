"""Read-only Explorer-style listing/search helpers for RecoveryDesk.

No source reads: these helpers only examine previously parsed entries. Unknown
metadata is explicitly displayed as unknown; never guess timestamps or types.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import PurePath
from typing import Iterable


@dataclass(frozen=True)
class SearchCriteria:
    name: str = ''
    extensions: str = ''
    min_bytes: int | None = None
    max_bytes: int | None = None
    kind: str = 'Alle'
    in_path: bool = False

    def validate(self) -> None:
        if self.min_bytes is not None and self.min_bytes < 0:
            raise ValueError('Mindestgröße darf nicht negativ sein.')
        if self.max_bytes is not None and self.max_bytes < 0:
            raise ValueError('Höchstgröße darf nicht negativ sein.')
        if (self.min_bytes is not None and self.max_bytes is not None
                and self.min_bytes > self.max_bytes):
            raise ValueError('Mindestgröße muss kleiner oder gleich der Höchstgröße sein.')
        if self.kind not in ('Alle', 'Nur Dateien', 'Nur Ordner'):
            raise ValueError('Ungültige Typauswahl.')


def file_extension(entry) -> str:
    if entry.is_directory:
        return ''
    name = str(entry.name)
    if name.startswith('.') and name.count('.') == 1:
        return ''
    i = name.rfind('.')
    return name[i:].casefold() if i > 0 and i < len(name) - 1 else ''


def is_temporary_file(entry) -> bool:
    """True for an entry with the .tmp suffix in its visible on-disk name.

    Applies to *all* entry types, including damaged/index-only records,
    orphaned entries, and directories whose names end in .tmp. A corrupted
    directory marked as a folder used to bypass the original file-only check.

    Trailing Windows filename decoration (spaces/dots) and invisible Unicode
    formatting marks are ignored for checking the extension only. The actual
    names and underlying filesystem index are never modified.
    """
    name = str(getattr(entry, 'name', ''))
    # Damaged directory metadata and raw NTFS names can contain trailing
    # whitespace, dots, or invisible formatting characters. Avoid accidentally
    # accepting unrelated extensions such as .tmpx or .tmp-backup.
    name = name.rstrip('\u200b\u200c\u200d\ufeff\u2060\u00a0\t\r\n .')
    return name.casefold().endswith('.tmp')


def visible_entries(entries: Iterable, show_tmp: bool = False) -> list:
    """Filter the Explorer presentation without changing the filesystem index."""
    if show_tmp:
        return list(entries)
    return [entry for entry in entries if not is_temporary_file(entry)]


def display_kind(entry) -> str:
    if entry.is_directory:
        return 'Ordner'
    ext = file_extension(entry)
    return f'{ext[1:].upper()}-Datei' if ext else 'Datei'


def display_size(number: int | None) -> str:
    if number is None or number < 0:
        return '—'
    if number < 1024:
        return f'{number} B'
    for unit, div in [('KiB', 1024), ('MiB', 1024**2), ('GiB', 1024**3), ('TiB', 1024**4)]:
        if number < div * 1024 or unit == 'TiB':
            return f'{number / div:,.1f} {unit}'
    return str(number)


def display_modified(entry) -> str:
    unix = getattr(entry, 'modified_unix', None)
    if unix is None:
        return '—'
    try:
        return datetime.fromtimestamp(unix, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    except (OverflowError, OSError, ValueError, TypeError):
        return '—'


def _normal_extensions(text: str) -> list[str]:
    result = []
    for value in text.replace(';', ',').split(','):
        ext = value.strip().casefold()
        if not ext:
            continue
        if ext in ('*', '*.*'):
            result.append('*')
        elif ext.startswith('*.'):
            result.append(ext[1:])
        elif not ext.startswith('.'):
            result.append('.' + ext)
        else:
            result.append(ext)
    return result



# File-type shortcuts for the advanced search dialog.  These use exactly the
# same extension filter as manually entered terms; no signatures are scanned.
EXTENSION_CATEGORIES: dict[str, tuple[str, ...]] = {
    'Bilder': ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'tif', 'tiff', 'webp',
               'heic', 'heif', 'avif', 'svg', 'dng', 'cr2', 'nef', 'arw'),
    'Videos': ('mp4', 'm4v', 'mov', 'avi', 'mkv', 'wmv', 'mpg', 'mpeg',
               'webm', 'flv', '3gp', 'ts', 'mts', 'm2ts'),
    'Audio': ('mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'opus', 'wma',
              'aif', 'aiff', 'mid', 'midi'),
    # Office: current and legacy MS Office, templates, macro-enabled formats,
    # Access, OneNote, Publisher, Visio, Project and Outlook messages.
    # LibreOffice / OpenOffice: OpenDocument, Flat OpenDocument, legacy StarOffice,
    # and common document/exchange formats. Search uses extensions only.
    'Dokumente': (
        'pdf', 'txt', 'rtf', 'csv', 'tsv', 'md', 'epub',
        # Microsoft Word
        'doc', 'docx', 'docm', 'dot', 'dotx', 'dotm', 'wbk',
        # Microsoft Excel
        'xls', 'xlsx', 'xlsm', 'xlsb', 'xlt', 'xltx', 'xltm',
        'xla', 'xlam', 'xlw',
        # Microsoft PowerPoint
        'ppt', 'pptx', 'pptm', 'pps', 'ppsx', 'ppsm',
        'pot', 'potx', 'potm', 'ppa', 'ppam', 'sldx', 'sldm', 'thmx',
        # Microsoft Access / OneNote / Publisher / Visio / Project / Outlook
        'mdb', 'mde', 'accdb', 'accde', 'accdr',
        'one', 'onepkg', 'onetoc2', 'pub',
        'vsd', 'vdx', 'vsdx', 'vsdm', 'vss', 'vssx', 'vssm',
        'vst', 'vstx', 'vstm', 'mpp', 'mpt', 'msg', 'oft',
        # LibreOffice, OpenOffice: standard OpenDocument
        'odt', 'ott', 'odm', 'oth', 'ods', 'ots',
        'odp', 'otp', 'odg', 'otg', 'odf', 'odb',
        # Flat OpenDocument and legacy OpenOffice/StarOffice
        'fodt', 'fods', 'fodp', 'fodg',
        'sxw', 'stw', 'sxc', 'stc', 'sxi', 'sti',
        'sxd', 'std', 'sxg', 'sxm', 'vor', 'uot', 'uos', 'uop',
    ),
    # Disk images are grouped under Archive as requested; they are not
    # necessarily compressed archive files.
    'Archive': ('zip', 'rar', '7z', 'tar', 'gz', 'tgz', 'bz2', 'xz',
                'cab', 'iso', 'zst', 'img', 'raw', 'dd'),
}


def append_category_extensions(existing: str, category: str) -> str:
    """Add a category's file extensions, preserving custom terms and order.

    Duplicate extensions are omitted regardless of case or the spelling
    ('PDF', '.pdf', '*.PDF'). Multiple categories can be combined (OR).
    """
    if category not in EXTENSION_CATEGORIES:
        raise ValueError(f'Unbekannte Dateikategorie: {category}')
    values = [part.strip() for part in existing.replace(';', ',').split(',') if part.strip()]
    seen = set(_normal_extensions(existing))
    for extension in EXTENSION_CATEGORIES[category]:
        normalized = '.' + extension.casefold()
        if normalized not in seen:
            values.append('*' + normalized)
            seen.add(normalized)
    return ', '.join(values)


def compile_search(criteria: SearchCriteria):
    """Compile a search once for repeated matches across very large indexes.

    This is metadata-only; no source sectors are read. The compiled closure
    preserves the semantics of matches_query and search_entries.
    """
    criteria.validate()
    term = criteria.name.strip().casefold()
    wildcard = '*' in term or '?' in term
    extensions = set(_normal_extensions(criteria.extensions))
    check_extensions = bool(extensions) and '*' not in extensions
    min_size = criteria.min_bytes
    max_size = criteria.max_bytes
    kind = criteria.kind
    in_path = criteria.in_path

    def match(entry, path=''):
        is_dir = entry.is_directory
        if kind == 'Nur Dateien' and is_dir:
            return False
        if kind == 'Nur Ordner' and not is_dir:
            return False
        if term:
            candidate = (path if in_path else str(entry.name)).casefold()
            if wildcard:
                if not fnmatchcase(candidate, term):
                    return False
            elif term not in candidate:
                return False
        if check_extensions and (is_dir or file_extension(entry) not in extensions):
            return False
        if min_size is not None or max_size is not None:
            if is_dir:
                return False
            size = getattr(entry, 'size', 0)
            if min_size is not None and size < min_size:
                return False
            if max_size is not None and size > max_size:
                return False
        return True
    return match


def matches_query(entry, criteria: SearchCriteria, path: str = '') -> bool:
    return compile_search(criteria)(entry, path)


def search_entries(entries: Iterable, criteria: SearchCriteria,
                   paths: dict[str, str] | None = None) -> list:
    match = compile_search(criteria)
    if paths is None or not criteria.in_path or not criteria.name.strip():
        return [entry for entry in entries if match(entry, entry.name)]
    return [entry for entry in entries if match(entry, paths.get(entry.key, entry.name))]


class EntryPaths(Mapping):
    """Read-only path mapping; file path strings have a bounded LRU cache.

    Retains entry references and shared parent prefixes, never a full string per
    file. Entries are a snapshot and must not be mutated while this map is used.
    """
    def __init__(self, entries, parents, cache_size=256):
        self._entries = entries
        self._parents = parents
        self._cache = OrderedDict()
        self._cache_size = cache_size

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, key):
        if key in self._cache:
            value = self._cache.pop(key)
        else:
            entry = self._entries[key]
            value = self._parents[entry.parent_record] + '\\' + entry.name
        self._cache[key] = value
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return value


def construct_paths(entries: Iterable, root: int = 5, max_depth: int = 256, *,
                    lazy: bool = False) -> Mapping[str, str]:
    """Build best-effort directory paths, preserving explicit orphan/cycle markers.

    Do not merge same-parent hard links; indexed file entry keys stay unique.
    Cyclic or absent directory parents are *not* represented as valid root paths.
    """
    seq = list(entries)
    dirs = {}
    for e in seq:
        if e.is_directory:
            dirs.setdefault(e.record_number, e)
    cache = {root: ''}

    def parent_path(parent: int) -> str:
        if parent in cache:
            return cache[parent]
        parts = []
        seen = set()
        cur = parent
        while cur not in cache:
            if cur in seen or len(parts) >= max_depth:
                prefix = '[Zyklischer Pfad]'
                break
            seen.add(cur)
            obj = dirs.get(cur)
            if obj is None:
                prefix = '[Nicht zugeordnet]'
                break
            parts.append((cur, obj.name))
            cur = obj.parent_record
        else:
            prefix = cache[cur]
        for record, name in reversed(parts):
            prefix += '\\' + name
            cache[record] = prefix
        return cache.get(parent, prefix)

    if lazy:
        parents = {}
        for e in seq:
            if e.parent_record not in parents:
                parents[e.parent_record] = parent_path(e.parent_record)
        return EntryPaths({e.key: e for e in seq}, parents)
    return {e.key: (parent_path(e.parent_record) + '\\' + e.name) for e in seq}


def sorted_entries(entries: Iterable, column: str, reverse: bool = False,
                   paths: dict[str, str] | None = None) -> list:
    """Consistent numeric/date sorting; unknown dates remain at bottom."""
    paths = paths or {}
    values = list(entries)
    values.sort(key=lambda e: (str(e.name).casefold(), e.record_number))
    if column == 'size':
        values.sort(key=lambda e: int(getattr(e, 'size', 0)), reverse=reverse)
    elif column == 'modified':
        known = [e for e in values if getattr(e, 'modified_unix', None) is not None]
        unknown = [e for e in values if getattr(e, 'modified_unix', None) is None]
        known.sort(key=lambda e: e.modified_unix, reverse=reverse)
        values = known + unknown
    elif column == 'mft':
        values.sort(key=lambda e: e.record_number, reverse=reverse)
    elif column == 'extension':
        values.sort(key=lambda e: file_extension(e), reverse=reverse)
    elif column == 'type':
        values.sort(key=lambda e: display_kind(e).casefold(), reverse=reverse)
    elif column == 'path':
        values.sort(key=lambda e: paths.get(e.key, '').casefold(), reverse=reverse)
    elif column == 'status':
        values.sort(key=lambda e: str(e.status).casefold(), reverse=reverse)
    elif column == 'quality':
        from .recovery_quality import assess
        values.sort(key=lambda e: str(assess(e).grade), reverse=reverse)
    else:
        values.sort(key=lambda e: (not e.is_directory, e.name.casefold()), reverse=reverse)
    return values
