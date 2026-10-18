"""Non-destructive recovery preflight for selected files and folders.

This is a METADATA assessment. A clean result does not prove that source
content is intact or that previously deleted clusters were not reused.
No source or destination is opened for writing by this module.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable

from .batch_export import plan_selection
from .recovery_quality import assess
from .recovery_evidence import (build_live_cluster_evidence,
                                deleted_stream_claim_issue, self_overlap_issue)

MAX_DETAIL_ROWS = 2000

@dataclass(frozen=True)
class PreflightItem:
    path: str
    state: str  # Ordner | Bereit | Warnung | Gesperrt
    details: tuple[str, ...]
    bytes_expected: int

@dataclass
class PreflightReport:
    items: list[PreflightItem] = field(default_factory=list)
    files: int = 0
    folders: int = 0
    ready: int = 0
    warnings: int = 0
    blocked: int = 0
    expected_bytes: int = 0

    def summary(self) -> str:
        return (f'{self.files} Dateien, {self.folders} Ordner | '
                f'{self.ready} bereit, {self.warnings} mit Warnung, '
                f'{self.blocked} nicht exportierbar | '
                f'{self.expected_bytes:,} gemeldete Dateibytes')

    def as_text(self) -> str:
        lines = ['Tenshi – Export-Vorabprüfung', '', self.summary(), '',
                 'Nur Metadatenprüfung. Keine Prüfung auf überschriebene Inhalte.',
                 'Dateiinhalte wurden nicht gelesen oder mit Originalen verglichen.', '']
        lines.append('NTFS: Bereits von vorhandenen Dateien belegte Cluster sperren einen Löschfund.')
        lines.append('Keine Überlappung beweist NICHT, dass gelöschte Daten unversehrt sind.')
        lines.append('')
        for row in self.items:
            lines.append(f'[{row.state}] {row.path} ({row.bytes_expected:,} Bytes)')
            lines.extend(f'    - {line}' for line in row.details)
        return '\n'.join(lines) + '\n'


def _orphan_reason(index, entry) -> str | None:
    """Describe missing/cyclic/mismatched NTFS ancestry without inventing a path.

    Index children may already attach a known parent-loss root to -1. Older
    on-disk parent identifiers need careful handling with reused MFT numbers.
    """
    children = getattr(index, 'children', {})
    if any(e is entry for e in children.get(-1, ())):
        return 'Elternverzeichnis nicht zugeordnet; Exportpfad kann abweichen.'
    by_record = getattr(index, 'by_record', None)
    if not by_record:
        return None  # Generic filesystems do not always expose inode parents.
    cur = entry
    visited = {int(entry.record_number)}
    for _ in range(1024):
        parent_id = int(cur.parent_record)
        if parent_id == 5:
            return None
        if parent_id in visited:
            return 'Zyklische Verzeichniszuordnung; ursprünglicher Pfad unsicher.'
        visited.add(parent_id)
        parent = by_record.get(parent_id)
        if parent is None or not getattr(parent, 'is_directory', False):
            return 'Elternverzeichnis fehlt oder ist kein Ordner; ursprünglicher Pfad unsicher.'
        parent_sequence = getattr(cur, 'parent_sequence', 0)
        if parent_sequence and parent_sequence != getattr(parent, 'sequence', 0):
            return 'MFT-Elternreferenz verweist auf eine andere Record-Generation.'
        if not getattr(cur, 'is_deleted', False) and getattr(parent, 'is_deleted', False):
            return 'Vorhandene Datei verweist auf einen gelöschten Elternordner.'
        cur = parent
    return 'Sehr lange Verzeichniskette; Zuordnung nicht vollständig geprüft.'


def _ntfs_stream_problem(index, entry) -> str | None:
    """Validate NTFS run boundaries and initialized length without disk I/O."""
    size = getattr(entry, 'size', 0)
    kind = getattr(entry, 'data_kind', None)
    if kind == 'resident':
        data = getattr(entry, 'resident_data', None)
        if data is None or len(data) != size:
            return 'Residente NTFS-Datenlänge stimmt nicht mit Dateigröße überein.'
        return None
    if kind != 'nonresident':
        return 'Unbekannte NTFS-Datenzuordnung.'
    info = getattr(index, 'info', None)
    if info is None or getattr(info, 'cluster_size', 0) <= 0:
        return 'NTFS-Clustergröße unbekannt.'
    initialized = getattr(entry, 'initialized_size', -1)
    if not isinstance(initialized, int) or not 0 <= initialized <= size:
        return 'NTFS-Größe des initialisierten Datenbereichs ungültig.'
    cluster_size = info.cluster_size
    available = 0
    total_clusters = getattr(info, 'total_sectors', 0) * getattr(info, 'bytes_per_sector', 0) // cluster_size
    for run in getattr(entry, 'data_runs', []):
        n, lcn = getattr(run, 'clusters', 0), getattr(run, 'lcn', None)
        if not isinstance(n, int) or n <= 0 or (lcn is not None and
                (lcn < 0 or lcn + n > total_clusters)):
            return 'NTFS-Datenbereich liegt außerhalb des Volumes oder hat ungültige Länge.'
        available += n * cluster_size
    overlap = self_overlap_issue(entry)
    if overlap:
        return overlap
    if available < initialized:
        return 'NTFS-Clusterzuordnung deckt den initialisierten Dateibereich nicht vollständig ab.'
    return None


def inspect_metadata(index, path: str, entry, *, filesystem: str | None = None,
                     allocation_evidence=None) -> PreflightItem:
    """Pure classification; conservative warnings, no promises of intact data."""
    is_dir = bool(getattr(entry, 'is_directory', False))
    size = getattr(entry, 'size', 0)
    issues = []
    blocked = False
    quality = assess(entry)
    if is_dir:
        if getattr(entry, 'metadata_only', False) or getattr(entry, 'unsupported_reason', ''):
            blocked = True
            issues.append('Ordner-Metadaten unvollständig; kein zuverlässiger rekursiver Export.')
        else:
            issues.append('Ordner wird nach verfügbaren Dateisystemeinträgen exportiert.')
    else:
        if not isinstance(size, int) or size < 0:
            blocked = True
            issues.append('Ungültige Dateigröße.')
            size = 0
        if not getattr(entry, 'recoverable', False) or getattr(entry, 'metadata_only', False):
            blocked = True
            issues.append(getattr(entry, 'unsupported_reason', '') or 'Keine unterstützten Dateidaten verfügbar.')
        if not blocked and (filesystem == 'NTFS' or (filesystem is None and hasattr(index, 'info'))):
            defect = _ntfs_stream_problem(index, entry)
            if defect:
                blocked = True
                issues.append(defect)
            elif getattr(entry, 'is_deleted', False) and getattr(entry, 'data_kind', None) == 'nonresident':
                if allocation_evidence is None:
                    allocation_evidence = build_live_cluster_evidence(index)
                conflict = deleted_stream_claim_issue(entry, allocation_evidence)
                if conflict:
                    blocked = True
                    issues.append(conflict)
    if not blocked:
        if getattr(entry, 'is_deleted', False):
            issues.append('Gelöscht: freie Cluster können bereits überschrieben sein.')
        missing_parent = _orphan_reason(index, entry)
        if missing_parent:
            issues.append(missing_parent)
        if getattr(index, 'scan_warnings', ()):
            issues.append('Dateisystemscan meldete Auffälligkeiten; weitere Prüfung empfohlen.')
    if blocked:
        state = 'Gesperrt'
    elif is_dir:
        state = 'Warnung' if getattr(entry, 'is_deleted', False) or _orphan_reason(index, entry) or getattr(index, 'scan_warnings', ()) else 'Ordner'
    elif issues:
        state = 'Warnung'
    else:
        state = 'Bereit'
        issues.append('Metadaten plausibel; Dateiinhalt bleibt ungeprüft.')
    return PreflightItem(path, state, tuple(issues), 0 if is_dir else int(size))


def inspect_selection(index, selection: Iterable, *, filesystem: str | None = None,
                      max_items: int = 500_000) -> PreflightReport:
    """Inspect the same recursive item plan used by the real batch exporter."""
    # Keep the real export plan as the single authority for paths/collisions.
    plan = plan_selection(index, selection)
    if len(plan) > max_items:
        raise ValueError('Die Vorabprüfung enthält zu viele Einträge.')
    report = PreflightReport()
    evidence = (build_live_cluster_evidence(index)
                if hasattr(index, 'info') and any(not task.is_directory and
                    getattr(task.entry, 'is_deleted', False) and
                    getattr(task.entry, 'data_kind', None) == 'nonresident'
                    for task in plan) else None)
    for task in plan:
        checked = inspect_metadata(index, task.path, task.entry, filesystem=filesystem,
                                   allocation_evidence=evidence)
        report.items.append(checked)
        if task.is_directory:
            report.folders += 1
        else:
            report.files += 1
            if checked.state != 'Gesperrt':
                report.expected_bytes += checked.bytes_expected
        if checked.state == 'Bereit':
            report.ready += 1
        elif checked.state == 'Warnung':
            report.warnings += 1
        elif checked.state == 'Gesperrt':
            report.blocked += 1
    return report
