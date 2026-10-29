"""Deterministic resumable, read-only-source recovery batches.

A batch is tied to an exact source/selection snapshot, exports into its own
folder, records SHA-256 of completed outputs, and never overwrites a file.
Resume restarts unfinished files, NOT their already written partial bytes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Callable, Iterable

from .resilience import atomic_replace_json, is_transient_lock
from .diagnostics import traced, log_issue
from .ntfs_browser import safe_name, export_file as export_ntfs_file
from .filesystems import export_file as export_other_file
from .export_io import ExportCancelled
from .export_errors import export_error_message
from .sources import ensure_safe_destination, is_device_source, source_size
from .device_identity import capture_device_identity, check_device_identity, DeviceSourceChanged
from .secure_target import (mkdir_checked, atomic_json_checkpoint,
                            atomic_bytes_checkpoint, open_regular_input)

PLAN_LIMIT = 500_000
MANIFEST = 'recoverydesk_status.json'
LOG_NAME = 'recoverydesk_export_report.txt'


@dataclass
class PlannedItem:
    path: str  # canonical POSIX-style path relative to <batch>/files/
    entry: object
    is_directory: bool


@dataclass
class BatchResult:
    exported: int = 0
    directories: int = 0
    verified_existing: int = 0
    skipped: int = 0
    failed: int = 0
    total: int = 0
    bytes_written: int = 0
    cancelled: bool = False
    resumed: bool = False
    errors: list[str] = field(default_factory=list)
    root: str = ''
    manifest: str = ''
    log: str = ''
    checksums: str = ''
    checksum_errors: list[str] = field(default_factory=list)


def _json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _digest(value) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _identity(source: str, index) -> dict:
    expected = getattr(index, '_device_identity', None)
    try:
        identity = _read_identity(source, index)
        if expected is not None and identity.get('device_snapshot') != expected:
            raise DeviceSourceChanged('Datenträger wurde ausgetauscht oder geändert. Quelle erneut einlesen.')
        return identity
    except DeviceSourceChanged:
        raise
    except (OSError, ValueError) as exc:
        if expected is not None:
            raise DeviceSourceChanged('Quelle nicht mehr erreichbar. Datenträger erneut einlesen.') from exc
        raise


def _read_identity(source: str, index) -> dict:
    # Identity is a useful consistency check, not a cryptographic fingerprint of the source disk.
    identity = {'source': os.path.normcase(os.path.abspath(source)),
                'size': source_size(source),
                'filesystem': str(getattr(index, 'filesystem', 'NTFS')),
                'offset': int(getattr(index, 'offset', getattr(getattr(index, 'info', None), 'partition_offset', 0)))}
    if identity['filesystem'] == 'exFAT':
        # Old exports may contain undefined physical bytes beyond ValidDataLength.
        identity['reader_semantics'] = 'exfat-valid-data-length-v1'
    if not is_device_source(source):
        st = os.stat(source)
        identity['modified_ns'] = st.st_mtime_ns
        # A bounded fingerprint of the beginning of an image, not the whole image.
        with open(source, 'rb') as f:
            identity['header_sha256'] = hashlib.sha256(f.read(65536)).hexdigest()
    else:
        snapshot = capture_device_identity(source, identity['offset'])
        expected = getattr(index, '_device_identity', None)
        if expected is not None and snapshot != expected:
            raise DeviceSourceChanged('Datenträger wurde ausgetauscht oder geändert. Quelle erneut einlesen.')
        identity['device_snapshot'] = snapshot
        identity['device_warning'] = 'Gerätekennungen sind kein Nachweis identischer oder intakter Dateiinhalte.'
    return identity


def _key(entry) -> str:
    return str(getattr(entry, 'key', f'{entry.record_number}:0'))


def _selected_roots(index, selection: Iterable[object]) -> list:
    unique = {_key(e): e for e in selection}
    # If an ancestor directory is selected, drop descendants from top-level selection.
    by_id = {int(e.record_number): e for e in index.entries if e.is_directory}
    chosen_dirs = {int(e.record_number) for e in unique.values() if e.is_directory}
    result = []
    for e in unique.values():
        p = int(e.parent_record)
        trail = {int(e.record_number)}
        covered = False
        while p not in trail and p in by_id:
            if p in chosen_dirs:
                covered = True
                break
            trail.add(p)
            p = int(by_id[p].parent_record)
        if not covered:
            result.append(e)
    return sorted(result, key=lambda e: (e.name.casefold(), _key(e)))


def plan_selection(index, selection: Iterable[object]) -> list[PlannedItem]:
    """Stable export paths; reject cycles and ambiguous names safely."""
    roots = _selected_roots(index, selection)
    stack = [(item, '', frozenset()) for item in reversed(roots)]
    items = []
    used_per_parent: dict[str, set[str]] = {}
    while stack:
        entry, parent, ancestors = stack.pop()
        if len(items) >= PLAN_LIMIT:
            raise ValueError(f'Export umfasst mehr als {PLAN_LIMIT:,} Einträge.')
        eid = int(entry.record_number)
        if eid in ancestors:
            continue
        used = used_per_parent.setdefault(parent, set())
        name = safe_name(entry.name, eid)
        proposed = name
        if proposed.casefold() in used:
            stem, extension = os.path.splitext(name)
            proposed = f'{stem[:100]}__ID{eid}_{getattr(entry, "link_index", 0)}{extension}'
            n = 2
            while proposed.casefold() in used:
                proposed = f'{stem[:80]}__ID{eid}_{n}{extension}'
                n += 1
        used.add(proposed.casefold())
        rel = f'{parent}/{proposed}' if parent else proposed
        items.append(PlannedItem(rel, entry, bool(entry.is_directory)))
        if entry.is_directory and not getattr(entry, 'metadata_only', False):
            # Unsupported directories are included as errors, not traversed.
            if getattr(entry, 'unsupported_reason', ''):
                continue
            children = index.list_dir(eid)
            stack.extend((child, rel, ancestors | {eid}) for child in reversed(children))
    return items


def _task_desc(item: PlannedItem) -> dict:
    e = item.entry
    descriptor = {'path': item.path, 'id': _key(e), 'size': int(e.size),
            'directory': item.is_directory, 'deleted': bool(e.is_deleted),
            'locator': str(getattr(e, 'locator', '')),
            'data_kind': getattr(e, 'data_kind', None),
            'reason': getattr(e, 'unsupported_reason', '')}
    if getattr(e, 'valid_data_length', None) is not None:
        descriptor['valid_data_length'] = e.valid_data_length
    return descriptor


def _atomic_json(dest: Path, data: dict, *, source: str | None = None):
    """Persist a manifest; anchor Linux writes to a checked dirfd."""
    if source is not None and sys.platform.startswith('linux'):
        atomic_json_checkpoint(str(dest), data, source)
    else:
        atomic_replace_json(dest, data)


def _write_log(path: Path, state: dict, result: BatchResult):
    from .verification_labels import EXPORT_SCOPE, RESUME_SCOPE, export_status_label
    rows = [f'Tenshi Exportbericht — {datetime.now(timezone.utc).isoformat()}',
            f'Quelle: {state["identity"]["source"]}',
            f'Dateisystem: {state["identity"]["filesystem"]}',
            f'Exportziel: {result.root}',
            f'Status: {"Abgebrochen" if result.cancelled else "Beendet mit Fehlern" if result.failed or result.checksum_errors else "Beendet"}',
            f'Neue Dateien: {result.exported}; Export-Prüfsumme bestätigt: {result.verified_existing}',
            f'Neue Ordner: {result.directories}; fehlgeschlagen: {result.failed}; ausgelassen: {result.skipped}',
            f'Prüfsummendatei: {result.checksums or "Einzeldateien / noch nicht zusammengefasst"}',
            *[f'Prüfsummendateien: {error}' for error in result.checksum_errors],
            '', EXPORT_SCOPE, RESUME_SCOPE, '', 'Einzelergebnisse:']
    for key, item in sorted(state['results'].items()):
        rows.append(f'{export_status_label(item["status"])}\t{key}\t{item.get("detail", "")}')
        confirmed = item.get('sha256')
        copied = item.get('copied_sha256')
        if (item['status'] == 'Erfolgreich' and not item.get('verification_pending')
                and isinstance(confirmed, str) and re.fullmatch(r'[0-9a-f]{64}', confirmed)):
            rows.append(f'  SHA256 (Zieldatei bestätigt): {confirmed}')
        elif isinstance(copied, str) and re.fullmatch(r'[0-9a-f]{64}', copied):
            rows.append(f'  SHA256 (kopierter Datenstrom; Zielprüfung nicht bestätigt): {copied}')
        else:
            rows.append('  SHA256: nicht verfügbar (z. B. Ordner oder unvollständiger Export)')
    text = '\n'.join(rows) + '\n'
    source = state['identity']['source']
    if sys.platform.startswith('linux'):
        atomic_bytes_checkpoint(str(path), text.encode('utf-8'), source)
        return
    # Use a unique temp file; stale .tmp files must not block later exports.
    from tempfile import NamedTemporaryFile
    from .resilience import RETRY_DELAYS
    temp = None
    try:
        with NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                               prefix='.tenshi-report-', suffix='.tmp', delete=False) as f:
            temp = Path(f.name)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        for delay in (*RETRY_DELAYS, None):
            try:
                if _is_unsafe_link(path):
                    raise ValueError('Berichtsziel wurde auf einen Link umgeleitet.')
                os.replace(temp, path)
                temp = None
                break
            except OSError as exc:
                if delay is None or not is_transient_lock(exc):
                    raise
                time.sleep(delay)
    finally:
        if temp is not None:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass


def _hash_file(path: Path, *, source: str | None = None,
               cancel: Callable[[], bool] | None = None,
               progress: Callable[[int], None] | None = None) -> str:
    """Verify an output by its opened inode, checking cancellation per MiB."""
    digest = hashlib.sha256()
    def check_cancel():
        if cancel and cancel():
            raise ExportCancelled('SHA-256-Prüfung abgebrochen.')
    def read_digest(stream):
        before = os.fstat(stream.fileno())
        named_before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('Nur reguläre Exportdateien dürfen geprüft werden.')
        read_bytes = 0
        if progress:
            progress(0)
        while True:
            check_cancel()
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            if read_bytes + len(chunk) > before.st_size:
                raise OSError('Exportdatei während der Prüfung geändert.')
            digest.update(chunk)
            read_bytes += len(chunk)
            if progress:
                progress(read_bytes)
        check_cancel()
        after = os.fstat(stream.fileno())
        current = path.lstat()
        identity = lambda meta: (meta.st_dev, meta.st_ino, meta.st_size,
                                 meta.st_mtime_ns, meta.st_ctime_ns)
        # Windows may report different timestamp values through fstat and
        # lstat for the same file. Compare timestamps only within each API.
        same_file = lambda meta: (meta.st_dev, meta.st_ino, meta.st_size)
        if (read_bytes != before.st_size or identity(before) != identity(after) or
                identity(named_before) != identity(current) or
                same_file(after) != same_file(current) or
                not stat.S_ISREG(current.st_mode)):
            raise OSError('Exportdatei während der Prüfung geändert.')
    check_cancel()
    if source is not None and sys.platform.startswith('linux'):
        with open_regular_input(str(path), source) as stream:
            read_digest(stream)
    else:
        with path.open('rb') as stream:
            read_digest(stream)
    return digest.hexdigest()


def _pending_copy(prior: dict, size: int) -> bool:
    """Only our completed-copy checkpoint can authorize a new hash attempt.

    Older cancelled exports and foreign files have no copied-stream digest.
    Never infer authorization from a human-readable error message or size alone.
    """
    return (prior.get('verification_pending') is True and
            prior.get('status') in ('Abgebrochen', 'Fehler') and
            type(prior.get('bytes')) is int and prior['bytes'] == size and
            isinstance(prior.get('copied_sha256'), str) and
            re.fullmatch(r'[0-9a-f]{64}', prior['copied_sha256']) is not None)


def _is_unsafe_link(path: Path) -> bool:
    """Reject symbolic links and Windows reparse-point junctions."""
    if path.is_symlink():
        return True
    if os.name == 'nt' and path.exists():
        try:
            # FILE_ATTRIBUTE_REPARSE_POINT includes junctions on Windows.
            return bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)
        except OSError:
            return True
    return False


def _safe_dir(path: Path, content: Path):
    """No existing symlink/reparse-point through the destination tree."""
    parent = path
    while True:
        if _is_unsafe_link(parent):
            raise ValueError(f'Symbolischer Link im Exportpfad nicht erlaubt: {parent}')
        if parent == content:
            break
        if content not in parent.parents:
            raise ValueError('Ungültiger relativer Exportpfad.')
        parent = parent.parent


@traced("batch_export")
def export_batch(source: str, index, selection: Iterable[object], target_dir: str,
                 progress: Callable[[int, int, str, str], None] | None = None,
                 byte_progress: Callable[[int], None] | None = None,
                 cancel: Callable[[], bool] | None = None,
                 event: Callable[[dict], None] | None = None,
                 expected_root: str | None = None) -> BatchResult:
    """Run or resume a batch using the same selected entries and destination.

    Fully completed files are trusted only when both size and SHA-256 match the
    previous checkpoint. Failed/cancelled files are retried in a later run.
    Existing untracked files are *never* overwritten or reclassified as done.
    """
    if not os.path.isdir(target_dir):
        raise ValueError('Zielordner nicht vorhanden.')
    ensure_safe_destination(source, target_dir)
    plan = plan_selection(index, selection)
    if not plan:
        raise ValueError('Keine Einträge ausgewählt.')
    identity = _identity(source, index)
    device_snapshot = identity.get('device_snapshot')
    last_device_check = time.monotonic()
    def check_device(force=False):
        nonlocal last_device_check
        now = time.monotonic()
        if device_snapshot is not None and (force or now - last_device_check >= .5):
            check_device_identity(source, device_snapshot)
            last_device_check = now
    source_changed = False
    signature = _digest({'identity': identity, 'tasks': [_task_desc(i) for i in plan]})
    # New exports use the Tenshi brand; existing RecoveryDesk jobs keep their
    # original directory for trustworthy checkpoint-based resume.
    new_root = Path(target_dir) / f'Tenshi_Export_{signature[:16]}'
    old_root = Path(target_dir) / f'RecoveryDesk_Export_{signature[:16]}'
    root = new_root if new_root.exists() or not old_root.exists() else old_root
    if expected_root is not None:
        normalize=lambda path:os.path.normcase(os.path.abspath(path))
        if normalize(root)!=normalize(expected_root) or not root.is_dir():
            raise ValueError('Der bisherige Export kann nicht fortgesetzt werden: Quelle, Auswahl oder Exportordner wurde geändert. Bitte Quelle und Exportordner prüfen.')
    content = root / 'files'
    manifest_path = root / MANIFEST
    log_path = root / LOG_NAME
    result = BatchResult(total=len(plan), root=str(root), manifest=str(manifest_path), log=str(log_path))
    if _is_unsafe_link(root):
        raise ValueError('Exportziel ist ein symbolischer Link.')
    if root.exists():
        if not root.is_dir() or not manifest_path.is_file() or _is_unsafe_link(manifest_path):
            raise FileExistsError('Exportverzeichnis existiert ohne gültigen Wiederaufnahme-Status.')
        if sys.platform.startswith('linux'):
            with open_regular_input(str(manifest_path), source) as f:
                state = json.load(f)
        else:
            with manifest_path.open('r', encoding='utf-8') as f:
                state = json.load(f)
        if state.get('schema') != 1 or state.get('signature') != signature or state.get('identity') != identity:
            raise ValueError('Bestehender Export gehört zu einer anderen Quelle/Auswahl.')
        if not isinstance(state.get('results'), dict):
            raise ValueError('Ungültige Export-Statusdatei.')
        result.resumed = True
    else:
        mkdir_checked(str(root), source)
        mkdir_checked(str(content), source)
        state = {'schema': 1, 'signature': signature, 'identity': identity,
                 'started': datetime.now(timezone.utc).isoformat(), 'results': {}}
        _atomic_json(manifest_path, state, source=source)
    if not content.is_dir() or _is_unsafe_link(content) or _is_unsafe_link(log_path):
        raise ValueError('Exportordner ist nicht sicher zugänglich.')
    from .export_checksums import ExportChecksums,ChecksumCheckpointError
    def persist_checksums():
        try:_atomic_json(manifest_path,state,source=source)
        except (OSError,ValueError) as exc:raise ChecksumCheckpointError(str(exc)) from exc
    checksums=ExportChecksums(root,source,state,persist_checksums)
    confirmed=[]
    exporter = export_ntfs_file if hasattr(index, 'info') else export_other_file
    from .recovery_preflight import inspect_metadata
    from .recovery_evidence import build_live_cluster_evidence
    allocation_evidence = (build_live_cluster_evidence(index)
                           if hasattr(index, 'info') and any(
                               not task.is_directory and getattr(task.entry, 'is_deleted', False)
                               and getattr(task.entry, 'data_kind', None) == 'nonresident'
                               for task in plan) else None)
    if event:
        # Limit the in-memory UI preview, not the actual export plan or report.
        preview_limit = 4000
        event({'type': 'plan', 'total': len(plan),
               'total_bytes': sum(max(0, int(i.entry.size)) for i in plan if not i.is_directory),
               'items': [{'path': i.path, 'size': max(0, int(i.entry.size)),
                          'directory': i.is_directory} for i in plan[:preview_limit]],
               'visible_limit': preview_limit, 'resumed': result.resumed,
               'root': str(root), 'log': str(log_path)})
    for n, task in enumerate(plan, start=1):
        if cancel and cancel():
            result.cancelled = True
            break
        check_device()
        path = content.joinpath(*task.path.split('/'))
        _safe_dir(path, content)
        ensure_safe_destination(source, str(path))
        prior = state['results'].get(task.path, {})
        completed_status = ''
        buffered_bytes = 0
        last_byte_event = time.monotonic()
        file_bytes = 0
        if event:
            event({'type': 'start', 'path': task.path, 'number': n,
                   'size': max(0, int(task.entry.size)) if not task.is_directory else 0})
        def on_bytes(delta):
            nonlocal buffered_bytes, last_byte_event, file_bytes
            file_bytes += delta
            check_device(force=file_bytes >= task.entry.size)
            if byte_progress:
                byte_progress(delta)
            if event:
                buffered_bytes += max(0, int(delta))
                now = time.monotonic()
                if now - last_byte_event >= .15:
                    event({'type': 'bytes', 'path': task.path, 'delta': buffered_bytes})
                    buffered_bytes = 0
                    last_byte_event = now
        def flush_bytes():
            nonlocal buffered_bytes
            if event and buffered_bytes:
                event({'type': 'bytes', 'path': task.path, 'delta': buffered_bytes})
                buffered_bytes = 0
        last_hash_event = 0.0
        def on_hash(read_bytes, *, existing=False):
            nonlocal last_hash_event
            now = time.monotonic()
            if event and (read_bytes == 0 or read_bytes >= task.entry.size or
                          now - last_hash_event >= .15):
                event({'type': 'verify', 'path': task.path, 'read': read_bytes,
                       'size': max(0, int(task.entry.size)), 'existing': existing})
                last_hash_event = now
        if progress:
            progress(n, len(plan), task.path, 'Prüfung')
        if task.is_directory:
            if getattr(task.entry, 'unsupported_reason', '') or getattr(task.entry, 'metadata_only', False):
                result.skipped += 1
                state['results'][task.path] = {'status': 'Übersprungen', 'detail': 'Verzeichnis-Metadaten unsicher'}
            elif path.exists():
                if not path.is_dir() or prior.get('status') != 'Ordner erstellt':
                    result.failed += 1
                    state['results'][task.path] = {'status': 'Fehler', 'detail': 'Vorhandener Ordner ohne passenden Status'}
                else:
                    state['results'][task.path] = {'status': 'Ordner erstellt'}
            else:
                copy_complete = False
                try:
                    if not path.parent.is_dir():
                        raise OSError('Übergeordneter Ordner konnte nicht erstellt werden.')
                    mkdir_checked(str(path), source)
                    result.directories += 1
                    state['results'][task.path] = {'status': 'Ordner erstellt'}
                except OSError as exc:
                    result.failed += 1
                    state['results'][task.path] = {'status': 'Fehler', 'detail': export_error_message(exc)}
        else:
            if not getattr(task.entry, 'recoverable', False):
                result.skipped += 1
                state['results'][task.path] = {'status': 'Übersprungen',
                    'detail': getattr(task.entry, 'unsupported_reason', 'Nicht exportierbar')}
            elif (preflight := inspect_metadata(index, task.path, task.entry,
                                               allocation_evidence=allocation_evidence)).state == 'Gesperrt':
                result.skipped += 1
                state['results'][task.path] = {'status': 'Übersprungen',
                    'detail': '; '.join(preflight.details)}
            elif path.exists() or _is_unsafe_link(path):
                try:
                    pending = _pending_copy(prior, task.entry.size)
                    expected = prior.get('copied_sha256') if pending else prior.get('sha256')
                    if ((pending or prior.get('status') == 'Erfolgreich') and
                            not _is_unsafe_link(path) and path.is_file() and
                            path.stat().st_size == task.entry.size and
                            _hash_file(path, source=source, cancel=cancel,
                                       progress=lambda read: on_hash(read, existing=True)) == expected):
                        check_device(force=True)
                        result.verified_existing += 1
                        completed_status = 'Bereits verifiziert'
                        if pending:
                            state['results'][task.path] = {
                                'status': 'Erfolgreich', 'bytes': task.entry.size,
                                'sha256': expected, 'copied_sha256': expected,
                                'detail': 'Mit der beim Kopieren gespeicherten Prüfsumme bestätigt'}
                            if getattr(index, 'filesystem', None) == 'exFAT':
                                state['results'][task.path]['valid_data_length'] = task.entry.valid_data_length
                    else:
                        result.failed += 1
                        state['results'][task.path] = {**(prior if pending else {}), 'status': 'Fehler',
                            'detail': 'Zieldatei existiert und kann nicht als vorheriger Export bestätigt werden'}
                except DeviceSourceChanged as exc:
                    source_changed = True
                    result.failed += 1
                    state['results'][task.path] = {**prior, 'status': 'Fehler', 'detail': str(exc)}
                except ExportCancelled:
                    result.cancelled = True
                    completed_status = 'Abgebrochen'
                    # Keep the prior checkpoint; a later run must hash it again.
                except (OSError, ValueError) as exc:
                    result.failed += 1
                    state['results'][task.path] = {**(prior if pending else {}), 'status': 'Fehler',
                        'detail': 'Vorhandene Exportdatei konnte nicht geprüft werden: '+export_error_message(exc)}
            else:
                copy_complete = False
                copied_digest = hashlib.sha256()
                pending_record = {}
                try:
                    if not path.parent.is_dir():
                        raise OSError('Übergeordneter Zielordner fehlt.')
                    if exporter is export_ntfs_file:
                        written = exporter(source, index.info, task.entry, str(path),
                                           cancel=cancel, byte_progress=on_bytes,
                                           data_digest=copied_digest)
                    else:
                        written = exporter(source, index, task.entry, str(path),
                                           cancel=cancel, byte_progress=on_bytes,
                                           data_digest=copied_digest)
                    copy_complete = True
                    pending_record = {'verification_pending': True, 'bytes': written,
                                      'copied_sha256': copied_digest.hexdigest()}
                    flush_bytes()
                    signature_file = _hash_file(path, source=source, cancel=cancel, progress=on_hash)
                    if signature_file != copied_digest.hexdigest():
                        raise OSError('Zieldatei stimmt nicht mit den kopierten Daten überein.')
                    result.exported += 1
                    result.bytes_written += written
                    state['results'][task.path] = {'status': 'Erfolgreich', 'bytes': written,
                                                   'sha256': signature_file,
                                                   'copied_sha256': copied_digest.hexdigest()}
                    if getattr(index, 'filesystem', None) == 'exFAT':
                        state['results'][task.path]['valid_data_length'] = task.entry.valid_data_length
                except DeviceSourceChanged as exc:
                    source_changed = True
                    result.failed += 1
                    state['results'][task.path] = {'status': 'Fehler', 'detail': str(exc)}
                except ExportCancelled:
                    result.cancelled = True
                    state['results'][task.path] = {**pending_record, 'status': 'Abgebrochen', 'detail': (
                        'Vollständig geschriebene Datei erhalten; SHA-256-Prüfung abgebrochen'
                        if copy_complete else 'Unvollständige Datei entfernt')}
                except (OSError, ValueError) as exc:
                    result.failed += 1
                    state['results'][task.path] = {**pending_record, 'status': 'Fehler', 'detail': export_error_message(exc)}
            if progress:
                progress(n, len(plan), task.path, state['results'].get(task.path, {}).get('status', ''))
        flush_bytes()
        current=state['results'].get(task.path,{})
        if not task.is_directory and not result.cancelled and current.get('status')=='Erfolgreich':
            digest=current.get('sha256','')
            confirmed.append((n,task.path,digest))
            try:
                if event:event({'type':'checksums','phase':'individual'})
                checksums.save_file(n,task.path,digest)
            except ChecksumCheckpointError:
                raise
            except (OSError,ValueError) as exc:
                result.checksum_errors.append(f'{task.path}: '+export_error_message(exc))
        _atomic_json(manifest_path, state, source=source)
        if event:
            current = state['results'].get(task.path, {})
            event({'type': 'done', 'path': task.path, 'number': n,
                   'status': completed_status or current.get('status', 'Unbekannt'),
                   'detail': current.get('detail', ''),
                   'size': max(0, int(task.entry.size)) if not task.is_directory else 0})
        if result.cancelled or source_changed:
            break
    if cancel and cancel():result.cancelled=True
    if not (result.cancelled or result.failed or result.skipped or result.checksum_errors):
        try:
            if event:event({'type':'checksums','phase':'summary'})
            result.checksums=checksums.finish(confirmed,cancel=cancel)
        except ChecksumCheckpointError:
            raise
        except (OSError,ValueError) as exc:
            # A fully saved summary may exist even if an individual file could
            # not be removed. Record its path only when its write completed.
            if checksums.summary_verified:result.checksums=str(root/'SHA256SUMS.sha256')
            result.checksum_errors.append(export_error_message(exc))
    if cancel and cancel():result.cancelled=True
    _write_log(log_path, state, result)
    result.errors = [f'{k}: {v.get("detail", "")}' for k,v in state['results'].items()
                     if v.get('status') in ('Fehler', 'Übersprungen', 'Abgebrochen')]
    result.errors.extend(result.checksum_errors)
    if event:
        event({'type': 'complete', 'cancelled': result.cancelled,'checksum_errors':bool(result.checksum_errors)})
    return result
