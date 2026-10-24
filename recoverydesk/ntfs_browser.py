"""Full NTFS $MFT folder index, independent of filename extension or file signatures.

Enumerates current AND deleted MFT entries (including directories) from a raw
NTFS volume. Directory relations come from $FILE_NAME parent file references;
this is not a reconstruction of damaged or overwritten directory indexes.
"""
from __future__ import annotations
from .secure_target import open_regular_output, mkdir_checked
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable
import os
import re
import struct

from .ntfs import (NTFSError, RunlistBoundsError, NTFSInfo, DataRun, parse_boot_sector,
                   apply_update_sequence, attributes, parse_runlist, iter_stream,
                   _read_exact, _u16, _u64)
from .sources import open_source, ensure_safe_destination, is_device_source
from .export_io import write_chunks, ExportCancelled
from .ntfs_reconstruct import (recover_attribute_stream, directory_index_hints,
                               directory_allocation_hints, IndexHint)

ROOT_RECORD = 5
ORPHANS = -1


class ScanCancelled(NTFSError):
    pass


@dataclass
class FileEntry:
    record_number: int
    sequence: int
    name: str
    parent_record: int
    parent_sequence: int
    is_directory: bool
    is_deleted: bool
    size: int = 0
    data_kind: str = 'none'
    initialized_size: int = 0
    data_runs: list[DataRun] = field(default_factory=list)
    resident_data: bytes | None = None
    unsupported_reason: str = ''
    link_index: int = 0
    metadata_only: bool = False  # Unverified INDEX_ROOT name without usable MFT record
    modified_unix: int | None = None  # NTFS $STANDARD_INFORMATION, if present

    @property
    def key(self) -> str:
        return f'{self.record_number}:{self.link_index}'

    @property
    def recoverable(self) -> bool:
        return not self.is_directory and not self.unsupported_reason and self.data_kind in ('resident', 'nonresident')

    @property
    def status(self) -> str:
        if self.metadata_only:
            return 'Nur Verzeichnisindex (unbestätigt, kein Dateiexport)'
        if self.is_deleted:
            return 'Gelöscht (Daten möglicherweise überschrieben)'
        return 'Vorhanden'


def _record_allocation_state(raw, info):
    """Classify header flags only after validating the complete record fixups."""
    try:
        record = apply_update_sequence(raw, info.bytes_per_sector)
        return 'in_use' if _u16(record, 22) & 1 else 'deleted'
    except (NTFSError, ValueError, OverflowError, struct.error):
        return 'unknown'


MAX_ATTRIBUTE_BASES = 10_000


@dataclass
class FileIndex:
    info: NTFSInfo
    entries: list[FileEntry]
    total_records: int
    scanned_records: int
    by_record: dict[int, FileEntry] = field(default_factory=dict)
    children: dict[int, list[FileEntry]] = field(default_factory=dict)
    orphan_count: int = 0
    damaged_records: int = 0  # FILE headers with invalid MFT metadata
    unreadable_records: int = 0  # skipped due to underlying I/O failures
    read_error_ranges: list[tuple[int, int]] = field(default_factory=list)
    scan_warnings: list[str] = field(default_factory=list)
    tolerant: bool = False
    reconstructed_index_hints: int = 0
    resolved_attribute_lists: int = 0
    unresolved_attribute_lists: int = 0
    allocation_index_hints: int = 0
    orphan_roots: int = 0
    orphan_cycles: int = 0
    record_error_reasons: dict[str, int] = field(default_factory=dict)
    record_error_states: dict[str, int] = field(default_factory=dict)
    record_error_samples: list[dict] = field(default_factory=list)
    attribute_list_limit_skipped: int = 0
    index_parse_failures: int = 0
    deleted_outside_volume_records: int = 0

    def list_dir(self, parent: int, show_deleted: bool = True) -> list[FileEntry]:
        items = self.children.get(parent, [])
        if not show_deleted:
            items = [entry for entry in items if not entry.is_deleted]
        return sorted(items, key=lambda e: (not e.is_directory, e.name.casefold(), e.record_number))


def _names_from_attrs(values: list[bytes]) -> list[tuple[str, int, int, int]]:
    names = []
    for value in values:
        if len(value) < 66:
            continue
        name_chars, ns = value[64], value[65]
        if name_chars == 0 or 66 + name_chars*2 > len(value):
            continue
        name = value[66:66+name_chars*2].decode('utf-16le', 'replace')
        ref = _u64(value, 0)
        names.append((name, ref & ((1 << 48)-1), ref >> 48, ns))
    # DOS 8.3 aliases are omitted only when a Win32 name for the same parent exists;
    # true hard links in different parents are retained.
    non_dos_parents = {p for n, p, s, ns in names if ns != 2}
    names = [x for x in names if x[3] != 2 or x[1] not in non_dos_parents]
    seen = set()
    unique = []
    for n, p, s, ns in sorted(names, key=lambda x: ({3:0, 1:1, 0:2, 2:3}.get(x[3], 4), x[0].casefold())):
        key = (n.casefold(), p, s)
        if key not in seen:
            seen.add(key)
            unique.append((n, p, s, ns))
    return unique


def _read_entry_records(raw: bytes, rec_no: int, info: NTFSInfo) -> list[FileEntry]:
    if raw[:4] != b'FILE':
        return []
    record = apply_update_sequence(raw, info.bytes_per_sector)
    if _u64(record, 32):  # base file reference of extension records
        return []
    sequence = _u16(record, 16)
    flags = _u16(record, 22)
    deleted = not (flags & 1)
    directory = bool(flags & 2)
    filename_attrs = []
    data_attrs = []
    has_attr_list = False
    modified_unix = None
    for typ, name, aflags, nonresident, payload in attributes(record):
        if typ == 0x10 and not nonresident and len(payload) >= 16:
            filetime = _u64(payload, 8)  # modification timestamp in 100-ns NT ticks
            # Do not display uninitialized/unplausible metadata as a real date.
            unix = (filetime - 116444736000000000) // 10000000
            if 0 <= unix < 32503680000:  # 1970-01-01 .. 2999-12-31
                modified_unix = unix
        if typ == 0x20:
            has_attr_list = True
        elif typ == 0x30 and not nonresident:
            filename_attrs.append(payload)
        elif typ == 0x80 and name == '':
            data_attrs.append((aflags, nonresident, payload))
    filenames = _names_from_attrs(filename_attrs)
    if not filenames:
        return []
    data_kind = 'none'
    size = 0
    initialized = 0
    resident = None
    runs: list[DataRun] = []
    unsupported = ''
    if has_attr_list:
        unsupported = 'Attributliste / Erweiterungsrecords werden nicht zusammengeführt'
    if not directory:
        if len(data_attrs) != 1:
            unsupported = unsupported or 'Kein eindeutiger unbenannter Datenstrom'
        else:
            aflags, nonresident, payload = data_attrs[0]
            if aflags & 0xC001:
                unsupported = unsupported or 'Komprimierte, verschlüsselte oder Sparse-Daten nicht unterstützt'
            if nonresident:
                data_kind = 'nonresident'
                first_vcn, last_vcn, size, initialized, raw_runs = payload
                if first_vcn != 0:
                    unsupported = unsupported or 'Fehlender erster VCN / mehrere Datenattribute'
                else:
                    runs = parse_runlist(raw_runs, info.total_sectors // info.sectors_per_cluster)
                    covered = sum(run.clusters for run in runs) * info.cluster_size
                    if size > covered or initialized > size or last_vcn + 1 != sum(r.clusters for r in runs):
                        unsupported = unsupported or 'Inkonsistente Datenstromlänge'
                    if any(run.lcn is None for run in runs):
                        # Sparse NTFS data is representable, but conservative about deleted entries.
                        unsupported = unsupported or 'Sparse-Datei wird nicht exportiert'
            else:
                data_kind = 'resident'
                resident = payload
                size = initialized = len(payload)
    result = []
    for i, (name, parent, parent_sequence, namespace) in enumerate(filenames):
        result.append(FileEntry(rec_no, sequence, name, parent, parent_sequence,
                                directory, deleted, size, data_kind, initialized,
                                runs, resident, unsupported, i, False, modified_unix))
    return result


def _mft_stream(f, info: NTFSInfo) -> tuple[list[DataRun], int]:
    raw = _read_exact(f, info.partition_offset + info.mft_lcn * info.cluster_size, info.record_size)
    record = apply_update_sequence(raw, info.bytes_per_sector)
    if _u64(record, 32):
        raise NTFSError('$MFT-Record 0 ist ein Erweiterungsrecord.')
    streams = []
    attr_list = False
    for kind, name, flags, nonresident, payload in attributes(record):
        if kind == 0x20:
            attr_list = True
        elif kind == 0x80 and name == '':
            streams.append((flags, nonresident, payload))
    if attr_list:
        raise NTFSError('$MFT-Attributliste nicht unterstützt; nicht alle Dateien können gelesen werden.')
    if len(streams) != 1 or not streams[0][1] or streams[0][0] & 0xC001:
        raise NTFSError('$MFT-Datenstrom nicht unterstützt.')
    first_vcn, last_vcn, size, initialized, raw_runs = streams[0][2]
    if first_vcn:
        raise NTFSError('Fehlender erster MFT-VCN.')
    runs = parse_runlist(raw_runs, info.total_sectors // info.sectors_per_cluster)
    covered = sum(run.clusters for run in runs) * info.cluster_size
    if size > covered or last_vcn + 1 != sum(r.clusters for r in runs):
        raise NTFSError('$MFT-Datenstrom nicht vollständig abgebildet.')
    return runs, size


def _read_mft_piece(f, info: NTFSInfo, runs: list[DataRun],
                    start: int, count: int) -> bytes:
    """Read a logical MFT slice. Preserve incomplete-stream failures."""
    return b''.join(iter_stream(f, info, runs, start * info.record_size,
                                count * info.record_size))


def _salvage_mft_batch(f, info: NTFSInfo, runs: list[DataRun],
                       start: int, count: int, *, max_retry_reads: int = 128,
                       cancel: Callable[[], bool] | None = None
                       ) -> tuple[list[tuple[int, bytes]], list[tuple[int, int]]]:
    """Bounded binary-split salvage on an IMAGE after a failed bulk read.

    Return good logical MFT records and unreadable record ranges. We never
    synthesize zero-filled records, write to source, or retry single records.
    This mode is intentionally not used on physical drives: extra reads can
    aggravate defective media.
    """
    found: list[tuple[int, bytes]] = []
    missing: list[tuple[int, int]] = []
    if count == 1:
        # The outer bulk-read already failed; do not retry the same sector.
        return [], [(start, start)]
    half = count // 2
    work = [(start + half, count - half), (start, half)]
    attempts = 0
    while work:
        if cancel and cancel():
            raise ScanCancelled('Scan wurde abgebrochen.')
        rec, n = work.pop()
        if attempts >= max_retry_reads:
            missing.append((rec, rec+n-1))
            continue
        attempts += 1
        try:
            block = _read_mft_piece(f, info, runs, rec, n)
            if len(block) != n * info.record_size:
                raise NTFSError('MFT-Datensatz unvollständig.')
            for pos in range(n):
                found.append((rec+pos, block[pos*info.record_size:(pos+1)*info.record_size]))
        except (OSError, NTFSError):
            if n == 1:
                missing.append((rec, rec))
            else:
                half = n // 2
                work.append((rec+half, n-half))
                work.append((rec, half))
    return found, sorted(missing)


def scan_ntfs_tree(path: str, partition_offset: int = 0, max_records: int = 0,
                   progress: Callable[[int,int],None] | None = None,
                   cancel: Callable[[],bool] | None = None,
                   tolerate_read_errors: bool = False) -> FileIndex:
    """Build an NTFS file index; optionally salvage readable MFT ranges from images.

    In tolerant mode only regular image files are accepted; physical devices
    are rejected to avoid retrying dangerous failing media. Broken records are
    skipped rather than guessed. The resulting tree may be incomplete.
    """
    if max_records < 0 or max_records > 30_000_000:
        raise ValueError('MFT-Maximum: 0 (alles) bis 30.000.000 Datensätze.')
    if tolerate_read_errors and is_device_source(path):
        raise NTFSError('Fehlertolerante Suche erfordert eine Image-Datei. '
                        'Bitte zuerst ein sektorweises Abbild erstellen; '
                        'defekte Datenträger nicht mehrfach lesen.')
    entries = []
    damaged_records = 0
    record_error_reasons = {}
    record_error_states = {}
    deleted_outside_volume_records = 0
    record_error_samples = []
    attribute_list_limit_skipped = 0
    unreadable_records = 0
    failed_ranges = []
    warnings = []
    # Only retain exceptional base records; caching the whole $MFT is unsafe
    # on big volumes. A second bounded read fetches needed extension records.
    attr_bases: dict[int, bytes] = {}
    dir_hints: list[IndexHint] = []
    allocation_index_hints = 0
    allocation_parse_failures = 0
    with open_source(path) as f:
        info = parse_boot_sector(f, partition_offset)
        runs, mft_bytes = _mft_stream(f, info)
        total = mft_bytes // info.record_size
        count = min(total, max_records) if max_records else total
        batch_records = max(1, (8 * 1024 * 1024) // info.record_size)
        for start in range(0, count, batch_records):
            if cancel and cancel():
                raise ScanCancelled('Scan wurde abgebrochen.')
            n = min(batch_records, count - start)
            try:
                raw = _read_mft_piece(f, info, runs, start, n)
                if len(raw) != n * info.record_size:
                    raise NTFSError('Unvollständiger MFT-Datenbereich.')
                records = [(start+i, raw[i*info.record_size:(i+1)*info.record_size])
                           for i in range(n)]
            except (OSError, NTFSError) as exc:
                if not tolerate_read_errors:
                    raise NTFSError(f'MFT-Lesefehler bei Datensatz {start}–{start+n-1}: {exc}. '
                                    'Für beschädigte Images optional „Fehlertolerante Suche“ aktivieren.') from exc
                records, missing = _salvage_mft_batch(f, info, runs, start, n, cancel=cancel)
                unreadable_records += sum(end-first+1 for first,end in missing)
                failed_ranges.extend(missing)
                if len(warnings) < 20:
                    warnings.append(f'MFT-Bereich {start}–{start+n-1}: '
                                    f'{sum(end-first+1 for first,end in missing)} Datensätze nicht lesbar')
            for rec_no, rec in records:
                if cancel and cancel():
                    raise ScanCancelled('Scan wurde abgebrochen.')
                if rec[:4] != b'FILE':
                    continue
                try:
                    parsed = _read_entry_records(rec, rec_no, info)
                    entries.extend(parsed)
                    if parsed and not parsed[0].is_directory and parsed[0].unsupported_reason.startswith('Attributliste'):
                        if len(attr_bases) < MAX_ATTRIBUTE_BASES:
                            attr_bases[rec_no] = rec
                        else:
                            attribute_list_limit_skipped += 1
                            if attribute_list_limit_skipped == 1 and len(warnings) < 20:
                                warnings.append('Sicherheitslimit für NTFS-Attributlisten erreicht.')
                    if parsed and parsed[0].is_directory and len(dir_hints) < 100_000:
                        try:
                            dir_hints.extend(directory_index_hints(rec, info, rec_no,
                                                                   max_entries=20_000))
                            remaining = min(60_000, 100_000 - len(dir_hints))
                            if remaining > 0:
                                index_errors: list[str] = []
                                hints = directory_allocation_hints(
                                    f, rec, info, rec_no, max_entries=remaining,
                                    errors=index_errors)
                                dir_hints.extend(hints)
                                allocation_index_hints += len(hints)
                                allocation_parse_failures += len(index_errors)
                                if index_errors and len(warnings) < 20:
                                    warnings.append(f'Verzeichnisindex MFT {rec_no}: '
                                                    + '; '.join(index_errors[:3]))
                        except (NTFSError, OSError, ValueError, struct.error) as exc:
                            allocation_parse_failures += 1
                            # Corrupt index metadata must not hide the valid MFT entry.
                            if len(warnings) < 20:
                                warnings.append(f'Verzeichnisindex MFT {rec_no} teilweise unlesbar: {exc}')
                except (NTFSError, ValueError, OverflowError, struct.error) as exc:
                    damaged_records += 1
                    allocation_state = _record_allocation_state(rec, info)
                    record_error_states[allocation_state] = record_error_states.get(allocation_state, 0) + 1
                    if allocation_state == 'deleted' and isinstance(exc, RunlistBoundsError):
                        deleted_outside_volume_records += 1
                    reason = type(exc).__name__ + ': ' + str(exc).replace('\n', ' ')[:160]
                    if reason not in record_error_reasons and len(record_error_reasons) >= 20:
                        reason = 'Weitere Fehlergründe (zusammengefasst)'
                    record_error_reasons[reason] = record_error_reasons.get(reason, 0) + 1
                    if len(record_error_samples) < 20:
                        record_error_samples.append({'record': rec_no, 'reason': reason, 'state': allocation_state})
            if progress:
                progress(start+n, total)
        # Validate extension references against the actual MFT stream. Never
        # export a partial attribute list if one referenced extent is missing.
        resolved_lists = failed_lists = 0
        by_record_entries: dict[int, list[FileEntry]] = defaultdict(list)
        for entry in entries:
            by_record_entries[entry.record_number].append(entry)
        for base_no, raw_base in attr_bases.items():
            if cancel and cancel():
                raise ScanCancelled('Scan wurde abgebrochen.')
            try:
                extra_runs, size, initialized = recover_attribute_stream(
                    f, info, runs, total, base_no, raw_base)
                for entry in by_record_entries[base_no]:
                    entry.data_kind = 'nonresident'
                    entry.data_runs = extra_runs
                    entry.size = size
                    entry.initialized_size = initialized
                    entry.resident_data = None
                    entry.unsupported_reason = ''
                resolved_lists += 1
            except (NTFSError, OSError, ValueError, OverflowError, struct.error) as exc:
                failed_lists += 1
                if len(warnings) < 20:
                    warnings.append(f'MFT {base_no}: Attributliste nicht auflösbar ({exc})')
    result = FileIndex(info, entries, total, count,
                       damaged_records=damaged_records,
                       unreadable_records=unreadable_records,
                       read_error_ranges=failed_ranges,
                       scan_warnings=warnings,
                       tolerant=tolerate_read_errors)
    result.record_error_reasons = record_error_reasons
    result.record_error_states = record_error_states
    result.deleted_outside_volume_records = deleted_outside_volume_records
    result.record_error_samples = record_error_samples
    result.attribute_list_limit_skipped = attribute_list_limit_skipped
    result.index_parse_failures = allocation_parse_failures
    result.resolved_attribute_lists = resolved_lists
    result.unresolved_attribute_lists = failed_lists
    by_record = {}
    for entry in entries:
        if entry.record_number not in by_record:
            by_record[entry.record_number] = entry
    # Recreate a *name-only* placeholder only when an intact directory's
    # resident $I30 INDEX_ROOT refers to a missing MFT record. The index name
    # cannot prove data contents, so these placeholders are never exportable.
    hints_added = 0
    seen = set()
    for hint in sorted(dir_hints, key=lambda h: {3:0, 1:1, 0:2, 2:3}.get(h.namespace, 4)):
        # Only reconstruct records actually covered by this scan, never records
        # outside an explicitly configured MFT scan limit.
        if hint.record in by_record or hint.record < 6 or hint.record >= count:
            continue
        key = (hint.record, hint.sequence)
        if key in seen:
            continue
        seen.add(key)
        placeholder = FileEntry(hint.record, hint.sequence, hint.name,
                                hint.parent, hint.parent_sequence,
                                hint.is_directory, False,
                                unsupported_reason='Nur Indexmetadaten, MFT-Eintrag fehlt',
                                metadata_only=True)
        entries.append(placeholder)
        by_record[hint.record] = placeholder
        hints_added += 1
    result.reconstructed_index_hints = hints_added
    result.by_record = by_record
    # Ensure that every directory is reachable from either the NTFS root or
    # the explicit "Nicht zugeordnet" tree. A damaged parent reference can
    # create a disconnected *cycle* that previously made all its files
    # invisible in the GUI. Break one link per cycle deterministically.
    directory_parents: dict[int, int] = {}
    for entry in entries:
        if entry.is_directory and entry.record_number != ROOT_RECORD:
            parent = by_record.get(entry.parent_record)
            if (parent and parent.is_directory and
                (not entry.parent_sequence or parent.sequence == entry.parent_sequence) and
                (entry.is_deleted or not parent.is_deleted)):
                directory_parents.setdefault(entry.record_number, entry.parent_record)
    detached: set[int] = set()
    visited: set[int] = set()
    for start in directory_parents:
        if start in visited:
            continue
        chain: list[int] = []
        seen: dict[int, int] = {}
        curr = start
        while curr in directory_parents and curr not in visited:
            if curr in seen:
                cycle = chain[seen[curr]:]
                if cycle:
                    detached.add(min(cycle))
                break
            seen[curr] = len(chain)
            chain.append(curr)
            curr = directory_parents[curr]
        visited.update(chain)
    children: dict[int,list[FileEntry]] = defaultdict(list)
    for entry in entries:
        if entry.record_number == ROOT_RECORD:
            continue
        parent = by_record.get(entry.parent_record)
        valid_parent = (parent is not None and parent.is_directory and
                        (not entry.parent_sequence or parent.sequence == entry.parent_sequence))
        if valid_parent and not entry.is_deleted and parent.is_deleted:
            valid_parent = False
        if entry.parent_record == entry.record_number or (
                entry.record_number in detached and entry.is_directory):
            valid_parent = False
        key = entry.parent_record if valid_parent else ORPHANS
        children[key].append(entry)
    result.children = dict(children)
    result.orphan_roots = len(children.get(ORPHANS, []))
    result.orphan_cycles = len(detached)
    # Count *all* entries in the orphan branch, including files under orphaned
    # directories, rather than just direct top-level roots.
    discovered: set[str] = set()
    queue = list(children.get(ORPHANS, []))
    while queue:
        entry = queue.pop()
        if entry.key in discovered:
            continue
        discovered.add(entry.key)
        if entry.is_directory:
            queue.extend(children.get(entry.record_number, []))
    result.orphan_count = len(discovered)
    result.allocation_index_hints = allocation_index_hints
    if detached and len(warnings) < 20:
        warnings.append(f'{len(detached)} zyklische NTFS-Elternketten unter „Nicht zugeordnet“ angezeigt.')
    if allocation_parse_failures and len(warnings) < 20:
        warnings.append(f'{allocation_parse_failures} NTFS-Indexbereiche konnten nicht vollständig gelesen werden.')
    return result


_BAD_WINDOWS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_RESERVED = re.compile(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)', re.I)


def safe_name(value: str, record_number: int) -> str:
    """Sanitize untrusted on-disk filename; never permit path traversal."""
    value = _BAD_WINDOWS.sub('_', value).strip(' .')
    if not value or value in ('.', '..'):
        value = f'Eintrag_{record_number}'
    if _RESERVED.match(value):
        value = '_' + value
    if len(value) > 160:
        stem, suffix = os.path.splitext(value)
        value = stem[:max(20, 160-len(suffix))] + suffix[-25:]
    return value


def _new_path(folder: str, name: str, entry: FileEntry) -> str:
    raw = safe_name(name, entry.record_number)
    target = os.path.join(folder, raw)
    if os.path.lexists(target):
        stem, ext = os.path.splitext(raw)
        target = os.path.join(folder, f'{stem}__MFT{entry.record_number}_{entry.link_index}{ext}')
    if os.path.lexists(target):
        raise FileExistsError(f'Ziel existiert bereits: {target}')
    return target


def export_file(source: str, info: NTFSInfo, entry: FileEntry, dest: str,
                cancel=None, byte_progress=None) -> int:
    """Read-only source; buffered streaming export; remove partial target on errors."""
    if not entry.recoverable:
        raise NTFSError(entry.unsupported_reason or 'Nicht als Datei exportierbar.')
    if os.path.lexists(dest):
        raise FileExistsError(f'Die Zieldatei existiert bereits: {dest}')
    ensure_safe_destination(source, dest)
    created = False
    with open_source(source) as f:
        actual_info = parse_boot_sector(f, info.partition_offset)
        if actual_info != info:
            raise NTFSError('NTFS-Geometrie hat sich geändert; Analyse erneut starten.')
        try:
            with open_regular_output(dest, 'xb', source) as dst:
                created = True
                if entry.data_kind == 'resident':
                    raw = entry.resident_data if entry.resident_data is not None else b''
                    if len(raw) != entry.size:
                        raise NTFSError('Inkonsistente residente Daten.')
                    chunks = iter((raw,))
                else:
                    def iter_content():
                        yield from iter_stream(f, info, entry.data_runs, 0, entry.initialized_size)
                        rest = entry.size - entry.initialized_size
                        while rest:
                            take = min(rest, 1024*1024)
                            yield bytes(take)
                            rest -= take
                    chunks = iter_content()
                count = write_chunks(dst, chunks, cancel=cancel, byte_progress=byte_progress)
                if count != entry.size:
                    raise NTFSError(f'Unvollständiger Datenstrom: {count} von {entry.size} Bytes')
                dst.flush()
                os.fsync(dst.fileno())
        except Exception:
            if created:
                try: os.unlink(dest)
                except OSError: pass
            raise
    return count


@dataclass
class ExportReport:
    exported: int = 0
    directories: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    bytes_written: int = 0
    cancelled: bool = False


def export_selection(source: str, index: FileIndex, selection: Iterable[FileEntry],
                     target_dir: str, progress: Callable[[str],None] | None = None,
                     cancel: Callable[[],bool] | None = None,
                     byte_progress: Callable[[int], None] | None = None) -> ExportReport:
    """Export files and recursive folders to a destination directory without overwrites.

    Existing files are never overwritten, source disk is never modified. Folder
    exports walk in-memory MFT parent references; broken links are omitted.
    """
    if not os.path.isdir(target_dir):
        raise ValueError('Der Zielordner existiert nicht.')
    ensure_safe_destination(source, target_dir)
    report = ExportReport()
    selected = list(selection)
    stack: list[tuple[FileEntry, str, frozenset[int]]] = [(e, target_dir, frozenset()) for e in reversed(selected)]
    while stack:
        if cancel and cancel():
            report.errors.append('Export durch Benutzer abgebrochen.')
            report.cancelled = True
            break
        entry, folder, ancestors = stack.pop()
        if entry.record_number in ancestors:
            report.skipped += 1
            report.errors.append(f'Zyklischer Verzeichniseintrag: {entry.name}')
            continue
        try:
            target = _new_path(folder, entry.name, entry)
            if entry.metadata_only:
                report.skipped += 1
                report.errors.append(f'{entry.name}: Nur unbestätigter Verzeichnisindex, kein Export möglich')
                continue
            if entry.is_directory:
                ensure_safe_destination(source, target)
                mkdir_checked(target, source)
                report.directories += 1
                next_ancestors = ancestors | {entry.record_number}
                children = index.list_dir(entry.record_number)
                stack.extend((child, target, next_ancestors) for child in reversed(children))
            else:
                if not entry.recoverable:
                    report.skipped += 1
                    report.errors.append(f'{entry.name}: {entry.unsupported_reason or "nicht unterstützt"}')
                    continue
                count = export_file(source, index.info, entry, target,
                                    cancel=cancel, byte_progress=byte_progress)
                report.bytes_written += count
                report.exported += 1
                if progress:
                    progress(entry.name)
        except ExportCancelled:
            report.cancelled = True
            report.errors.append('Export während der Datei abgebrochen; unvollständige Zieldatei entfernt.')
            break
        except (OSError, ValueError, NTFSError) as ex:
            report.skipped += 1
            report.errors.append(f'{entry.name}: {ex}')
    return report
