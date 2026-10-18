"""Honest, metadata-only recovery status filters and folder warning propagation.

A warning never proves that file contents or the disk itself are damaged.
"""
from __future__ import annotations

from .recovery_quality import assess

FILTER_ALL = 'Alle Einträge'
FILTER_WARNINGS = 'Auffällige Einträge'
FILTER_POSSIBLE = 'Export möglich'
FILTER_DELETED = 'Gelöscht / unsicher'
FILTER_LIMITED = 'Eingeschränkt'
FILTER_BLOCKED = 'Nicht exportierbar'
FILTER_HINTS = 'Nur Namenshinweise'
FILTER_FOLDERS = 'Nur Ordner'

STATUS_FILTERS = (
    FILTER_ALL, FILTER_WARNINGS, FILTER_POSSIBLE, FILTER_DELETED,
    FILTER_LIMITED, FILTER_BLOCKED, FILTER_HINTS, FILTER_FOLDERS,
)

# Folders are kept separate: an unexportable folder is not a broken file.
_WARNING_GRADES = frozenset(('limited', 'blocked', 'unknown'))


def matches_status(entry, selected_filter: str) -> bool:
    """Test one entry; unknown filters safely behave like no filter."""
    if selected_filter == FILTER_ALL or selected_filter not in STATUS_FILTERS:
        return True
    quality = assess(entry)
    if selected_filter == FILTER_WARNINGS:
        return quality.grade in _WARNING_GRADES
    if selected_filter == FILTER_POSSIBLE:
        return quality.grade == 'possible'
    if selected_filter == FILTER_DELETED:
        return bool(getattr(entry, 'is_deleted', False))
    if selected_filter == FILTER_LIMITED:
        return quality.grade == 'limited'
    if selected_filter == FILTER_BLOCKED:
        return quality.grade == 'blocked'
    if selected_filter == FILTER_HINTS:
        return quality.grade == 'unknown'
    if selected_filter == FILTER_FOLDERS:
        return entry.is_directory
    return True


def filter_entries(entries, selected_filter: str):
    """Preserve ordering and identity, filter by reported recoverability."""
    return [e for e in entries if matches_status(e, selected_filter)]


def folder_warning_records(entries: list, root: int = 5) -> set[int]:
    """Return directory IDs containing an entry with known metadata limitations.

    Follow each problematic entry's recorded parent chain. Detect broken/cyclic
    references and do not invent links to the volume root for orphaned entries.
    Hard-linked files can have more than one FileEntry and are handled individually.
    """
    directory_parent = {}
    for entry in entries:
        if getattr(entry, 'is_directory', False):
            directory_parent.setdefault(entry.record_number, entry.parent_record)
    flagged = set()
    for entry in entries:
        if assess(entry).grade not in _WARNING_GRADES:
            continue
        if getattr(entry, 'is_directory', False):
            flagged.add(entry.record_number)
        parent = entry.parent_record
        seen = set()
        while parent not in seen:
            seen.add(parent)
            if parent == root:
                flagged.add(root)
                break
            if parent not in directory_parent:
                break
            flagged.add(parent)
            parent = directory_parent[parent]
    return flagged


def visual_status(entry):
    """Return safe display prefix, tag and a metadata-only explanatory message."""
    quality = assess(entry)
    if getattr(entry, 'is_directory', False) and getattr(entry, 'is_deleted', False):
        return '✕', 'deleted', 'Gelöschter Ordner; Zuordnung möglicherweise veraltet'
    if quality.grade == 'unknown':
        return '⚠', 'warning', 'Unbestätigter Dateiname aus Verzeichnis-Metadaten'
    if quality.grade in ('blocked', 'limited'):
        return '⚠', 'warning', 'Export eingeschränkt oder Metadaten nicht unterstützt'
    if quality.grade == 'uncertain':
        return '✕', 'deleted', 'Gelöschter Dateieintrag; Inhalt kann überschrieben sein'
    return '📁' if entry.is_directory else '📄', 'normal', quality.detail
