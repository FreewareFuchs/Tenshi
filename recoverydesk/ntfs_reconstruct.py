"""Conservative NTFS metadata reconstruction helpers.

Read-only; never infers physical clusters from directory names. Only valid
resident $ATTRIBUTE_LIST entries and resident $I30 INDEX_ROOT are used.
Unsupported/incomplete structures are rejected rather than guessed.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from .ntfs import (NTFSError, NTFSInfo, DataRun, apply_update_sequence,
                   attributes, iter_stream, parse_runlist)

MASK48 = (1 << 48) - 1


def u16(b: bytes, o: int) -> int:
    return struct.unpack_from('<H', b, o)[0]


def u32(b: bytes, o: int) -> int:
    return struct.unpack_from('<I', b, o)[0]


def u64(b: bytes, o: int) -> int:
    return struct.unpack_from('<Q', b, o)[0]


@dataclass(frozen=True)
class AttributeRef:
    kind: int
    lowest_vcn: int
    record: int
    sequence: int
    instance: int
    name: str


def read_attribute_list(record: bytes) -> list[AttributeRef]:
    """Read resident $ATTRIBUTE_LIST; reject non-resident or damaged lists."""
    lists = [(nonresident, payload) for kind, name, flags, nonresident, payload
             in attributes(record) if kind == 0x20 and not name]
    if not lists:
        return []
    if len(lists) != 1 or lists[0][0]:
        raise NTFSError('Nicht residente oder mehrfache NTFS-Attributliste nicht unterstützt.')
    blob = lists[0][1]
    if len(blob) > 1024 * 1024:
        raise NTFSError('NTFS-Attributliste überschreitet Sicherheitslimit.')
    refs = []
    pos = 0
    while pos < len(blob):
        if len(refs) >= 512 or pos + 26 > len(blob):
            raise NTFSError('Unvollständige NTFS-Attributliste.')
        kind = u32(blob, pos)
        length = u16(blob, pos+4)
        name_len = blob[pos+6]
        name_off = blob[pos+7]
        if length < 26 or pos + length > len(blob) or (name_len and
                (name_off < 26 or name_off + 2*name_len > length)):
            raise NTFSError('Beschädigte NTFS-Attributliste.')
        name = (blob[pos+name_off:pos+name_off+2*name_len].decode('utf-16le', 'replace')
                if name_len else '')
        ref = u64(blob, pos+16)
        refs.append(AttributeRef(kind, u64(blob, pos+8), ref & MASK48,
                                 ref >> 48, u16(blob, pos+24), name))
        pos += length
    return refs


def _stream_extent(record: bytes, instance: int, lowest_vcn: int):
    """Match one unnamed $DATA attribute by instance and lowest VCN."""
    pos = u16(record, 20)
    found = []
    while pos + 8 <= len(record):
        kind = u32(record, pos)
        if kind == 0xFFFFFFFF:
            break
        length = u32(record, pos+4)
        if length < 24 or pos + length > len(record):
            raise NTFSError('Beschädigter Erweiterungsrecord.')
        a = record[pos:pos+length]
        if kind == 0x80 and a[9] == 0 and u16(a, 14) == instance:
            if a[8] != 1 or length < 64 or u64(a, 16) != lowest_vcn:
                raise NTFSError('Nicht-residente Daten-Extent-Metadaten fehlen.')
            run_offset = u16(a, 32)
            if run_offset < 64 or run_offset >= len(a):
                raise NTFSError('Ungültige NTFS-Extent-Runlist.')
            found.append((u16(a, 12), u64(a, 16), u64(a, 24),
                          u64(a, 48), u64(a, 56), a[run_offset:]))
        pos += length
    if len(found) != 1:
        raise NTFSError('Daten-Extent fehlt oder ist nicht eindeutig.')
    return found[0]


def recover_attribute_stream(f, info: NTFSInfo, mft_runs: list[DataRun],
                             mft_records: int, base_no: int, base_raw: bytes):
    """Resolve a fragmented uncompressed unnamed $DATA attribute list.

    Returns (runs, real_size, initialized_size). Every referenced MFT record
    must be present, fixed-up, sequence-checked and linked to the base record.
    """
    base = apply_update_sequence(base_raw, info.bytes_per_sector)
    if u64(base, 32):
        raise NTFSError('Kein NTFS-Basisrecord.')
    base_sequence = u16(base, 16)
    refs = [ref for ref in read_attribute_list(base) if ref.kind == 0x80 and ref.name == '']
    if not refs or len(refs) > 128:
        raise NTFSError('Keine unterstützte vollständige Attributliste für $DATA.')
    # Named data streams and other attribute kinds are not part of unnamed $DATA.
    refs.sort(key=lambda r: r.lowest_vcn)
    if refs[0].lowest_vcn != 0 or len({r.lowest_vcn for r in refs}) != len(refs):
        raise NTFSError('Attributliste besitzt Lücken oder doppelte VCN-Bereiche.')
    all_runs: list[DataRun] = []
    current_vcn = 0
    size = initialized = None
    visited = set()
    for ref in refs:
        if ref.lowest_vcn != current_vcn:
            raise NTFSError('Lücke in den NTFS-Datenextents.')
        if ref.record >= mft_records or ref.record < 0:
            raise NTFSError('Attributliste referenziert einen fehlenden MFT-Datensatz.')
        key = (ref.record, ref.instance)
        if key in visited:
            raise NTFSError('Doppelte Referenz in der NTFS-Attributliste.')
        visited.add(key)
        if ref.record == base_no:
            record = base
        else:
            raw = b''.join(iter_stream(f, info, mft_runs,
                                       ref.record*info.record_size, info.record_size))
            record = apply_update_sequence(raw, info.bytes_per_sector)
            parent_ref = u64(record, 32)
            if (parent_ref & MASK48) != base_no or parent_ref >> 48 != base_sequence:
                raise NTFSError('Erweiterungsrecord verweist nicht auf den erwarteten Basisrecord.')
        if ref.sequence and ref.sequence != u16(record, 16):
            raise NTFSError('MFT-Sequenznummer im Erweiterungsrecord stimmt nicht.')
        flags, first_vcn, last_vcn, real, init, blob = _stream_extent(
            record, ref.instance, ref.lowest_vcn)
        if flags & 0xC001:
            raise NTFSError('Komprimierte, verschlüsselte oder Sparse-Extents nicht unterstützt.')
        runs = parse_runlist(blob, info.total_sectors // info.sectors_per_cluster)
        if not runs or any(r.lcn is None for r in runs):
            raise NTFSError('Sparse- oder leere Datenextents werden nicht exportiert.')
        covered = sum(r.clusters for r in runs)
        if last_vcn < first_vcn or covered != last_vcn-first_vcn+1:
            raise NTFSError('NTFS-Extent-Länge passt nicht zur VCN-Zuordnung.')
        if first_vcn == 0:
            size, initialized = real, init
        all_runs.extend(runs)
        current_vcn = last_vcn+1
    if size is None or initialized is None or initialized > size or size > current_vcn * info.cluster_size:
        raise NTFSError('NTFS-Datenstromgröße und Extent-Abdeckung widersprechen sich.')
    return all_runs, size, initialized


@dataclass(frozen=True)
class IndexHint:
    record: int
    sequence: int
    parent: int
    parent_sequence: int
    name: str
    is_directory: bool
    namespace: int = 1


def directory_index_hints(record: bytes, info: NTFSInfo, parent_record: int,
                          *, max_entries: int = 20_000) -> list[IndexHint]:
    """Parse only valid resident $I30 INDEX_ROOT names as *unverified hints*.

    No allocation index, slack space, or overwritten entries are guessed.
    An INDEX_ROOT entry never proves its file contents are still present.
    """
    fixed = apply_update_sequence(record, info.bytes_per_sector)
    if not (u16(fixed, 22) & 3) == 3:
        return []
    sequence = u16(fixed, 16)
    result = []
    for kind, name, flags, nonresident, payload in attributes(fixed):
        if kind != 0x90 or name != '$I30' or nonresident:
            continue
        if len(payload) < 32 or u32(payload, 0) != 0x30:
            raise NTFSError('Beschädigter NTFS-Verzeichnisindex.')
        rel = u32(payload, 16)
        used = u32(payload, 20)
        start, end = 16+rel, 16+used
        if rel < 16 or start > end or end > len(payload):
            raise NTFSError('Ungültige INDEX_ROOT-Grenzen.')
        pos = start
        while pos + 16 <= end:
            if len(result) >= max_entries:
                raise NTFSError('Verzeichnisindex zu groß.')
            ref = u64(payload, pos)
            entry_len, key_len, eflags = struct.unpack_from('<HHH', payload, pos+8)
            if entry_len < 16 or pos + entry_len > end or key_len > entry_len - 16:
                raise NTFSError('Ungültige INDEX_ROOT-Eintragsgröße.')
            if eflags & 2:  # End marker
                break
            key = payload[pos+16:pos+16+key_len]
            if len(key) >= 66:
                n = key[64]
                if (n and 66+n*2 <= len(key) and (u64(key, 0)&MASK48) == parent_record
                        and (u64(key, 0)>>48) in (0, sequence)):
                    fname = key[66:66+n*2].decode('utf-16le', 'replace')
                    if fname not in ('.', '..'):
                        hints = IndexHint(ref & MASK48, ref >> 48, parent_record, sequence,
                                          fname, bool(u32(key, 56) & 0x10000000), key[65])
                        result.append(hints)
            pos += entry_len
    return result


# The on-disk $I30 tree may place the great majority of large directory
# entries in non-resident $INDEX_ALLOCATION buffers (INDX records).  These
# entries are *hints* only, never a source of recoverable file contents.
def _fixed_index_buffer(raw: bytes, sector_size: int) -> bytes:
    """Validate the NTFS update-sequence array before parsing an INDX buffer."""
    if len(raw) < 64 or len(raw) % sector_size or raw[:4] != b'INDX':
        raise NTFSError('Ungültiger NTFS-INDX-Puffer.')
    usa_off, usa_count = u16(raw, 4), u16(raw, 6)
    if usa_off < 8 or usa_count != len(raw)//sector_size+1 or usa_off+usa_count*2 > len(raw):
        raise NTFSError('Beschädigtes INDX-Update-Sequence-Array.')
    usn = raw[usa_off:usa_off+2]
    data = bytearray(raw)
    for i in range(1, usa_count):
        end = i*sector_size-2
        if raw[end:end+2] != usn:
            raise NTFSError('INDX-Puffer enthält beschädigten Sektor-Fixup.')
        data[end:end+2] = raw[usa_off+2*i:usa_off+2*i+2]
    return bytes(data)


def _allocation_index_entries(buffer: bytes, directory_no: int, directory_seq: int,
                              limit: int) -> list[IndexHint]:
    """Read valid $FILE_NAME keys from one fixed-up INDX index buffer."""
    if len(buffer) < 64:
        raise NTFSError('INDX-Puffer unvollständig.')
    # An INDX buffer begins with a 24-byte record header followed by
    # INDEX_HEADER. Offsets in INDEX_HEADER are relative to its own start.
    entries_off, used, allocated = u32(buffer, 24), u32(buffer, 28), u32(buffer, 32)
    start, end = 24+entries_off, 24+used
    if entries_off < 16 or start > end or end > len(buffer) or used > allocated or 24+allocated > len(buffer):
        raise NTFSError('Beschädigte INDX-Eintragsgrenzen.')
    results = []
    pos = start
    while pos+16 <= end:
        if len(results) >= limit:
            raise NTFSError('INDX-Eintragslimit überschritten.')
        file_ref = u64(buffer, pos)
        length, key_length, flags = struct.unpack_from('<HHH', buffer, pos+8)
        if length < 16 or pos+length > end or key_length > length-16:
            raise NTFSError('Beschädigte INDX-Eintragslänge.')
        if flags & 2:   # terminator
            break
        if flags & ~3:
            raise NTFSError('Unbekannte INDX-Eintragsflags.')
        if flags & 1 and length < 24 + key_length:
            raise NTFSError('INDX-Unterknotenreferenz unvollständig.')
        key = buffer[pos+16:pos+16+key_length]
        if len(key) >= 66:
            parent_ref = u64(key, 0)
            name_chars, namespace = key[64], key[65]
            if (name_chars and namespace in (0, 1, 2, 3) and
                66+name_chars*2 <= len(key) and
                (parent_ref & MASK48) == directory_no and
                (parent_ref >> 48) in (0, directory_seq)):
                name = key[66:66+name_chars*2].decode('utf-16le', 'replace')
                if name not in ('.', '..') and file_ref & MASK48:
                    results.append(IndexHint(file_ref & MASK48, file_ref >> 48,
                                             directory_no, directory_seq, name,
                                             bool(u32(key, 56) & 0x10000000), namespace))
        pos += length
    return results


def directory_allocation_hints(f, record: bytes, info: NTFSInfo, directory_no: int,
                               *, max_bytes: int = 64*1024*1024,
                               max_entries: int = 60_000,
                               errors: list[str] | None = None) -> list[IndexHint]:
    """Inspect allocated $I30 INDX buffers using the index bitmap, read-only.

    Requires an intact resident INDEX_ROOT, one ordinary non-resident $I30
    INDEX_ALLOCATION, and a matching bitmap. Unsupported layouts are rejected
    conservatively. All results are unverified, name-only metadata hints.
    """
    fixed = apply_update_sequence(record, info.bytes_per_sector)
    if (u16(fixed, 22) & 3) != 3:
        return []
    root, allocation, bitmap = [], [], []
    for kind, name, flags, nonresident, payload in attributes(fixed):
        if name != '$I30':
            continue
        if kind == 0x90 and not nonresident:
            root.append(payload)
        elif kind == 0xA0:
            allocation.append((flags, nonresident, payload))
        elif kind == 0xB0:
            bitmap.append((flags, nonresident, payload))
    if not allocation:
        return []
    if len(root) != 1 or len(allocation) != 1 or len(bitmap) != 1:
        raise NTFSError('Unvollständige NTFS-Index-Allocation oder fehlende Index-Bitmap.')
    r = root[0]
    if len(r) < 32 or u32(r, 0) != 0x30:
        raise NTFSError('INDEX_ROOT ist ungültig.')
    buffer_size = u32(r, 8)
    if (buffer_size < info.bytes_per_sector or buffer_size > 65536 or
        buffer_size & (buffer_size-1) or buffer_size % info.bytes_per_sector):
        raise NTFSError('Nicht unterstützte NTFS-Indexpuffergröße.')
    flags, nonresident, payload = allocation[0]
    if not nonresident or flags & 0xC001:
        raise NTFSError('Komprimierte/verschlüsselte Index-Allocation nicht unterstützt.')
    vcn, last, size, init, runlist = payload
    if vcn != 0 or size > max_bytes or size == 0 or size % buffer_size or init < size:
        raise NTFSError('Index-Allocation ist zu groß, unvollständig oder fragmentiert nach Attributliste.')
    runs = parse_runlist(runlist, info.total_sectors // info.sectors_per_cluster)
    if any(x.lcn is None for x in runs) or sum(x.clusters for x in runs)*info.cluster_size < size or sum(x.clusters for x in runs) != last+1:
        raise NTFSError('Nicht unterstützte Index-Allocation-Runlist.')
    bm_flags, bm_nonresident, bm_payload = bitmap[0]
    if bm_flags & 0xC001:
        raise NTFSError('Komprimierte Index-Bitmap nicht unterstützt.')
    if bm_nonresident:
        bm_first, bm_last, bm_size, bm_init, bm_raw = bm_payload
        if bm_first or bm_size > 8*1024*1024 or bm_init < bm_size:
            raise NTFSError('Ungültige nicht-residente Index-Bitmap.')
        bm_runs = parse_runlist(bm_raw, info.total_sectors // info.sectors_per_cluster)
        if sum(x.clusters for x in bm_runs)*info.cluster_size < bm_size:
            raise NTFSError('Unvollständige Index-Bitmap.')
        bitmap_bytes = b''.join(iter_stream(f, info, bm_runs, 0, bm_size))
    else:
        bitmap_bytes = bm_payload
    records = size // buffer_size
    if records > 16_384 or (records+7)//8 > len(bitmap_bytes):
        raise NTFSError('INDEX_ALLOCATION überschreitet Anzahl-Bitmap-Limit.')
    hints = []
    seen = set()
    for i in range(records):
        if not bitmap_bytes[i//8] & (1 << (i%8)):
            continue  # unallocated slots may contain stale/wiped records
        try:
            raw = b''.join(iter_stream(f, info, runs, i*buffer_size, buffer_size))
            fixed_buffer = _fixed_index_buffer(raw, info.bytes_per_sector)
            parsed_hints = _allocation_index_entries(fixed_buffer, directory_no, u16(fixed, 16),
                                                     max_entries-len(hints))
        except (NTFSError, OSError, ValueError, struct.error) as exc:
            # Skip a torn individual index block without retrying it. This
            # preserves other valid blocks and never trusts the corrupt one.
            if errors is None:
                raise
            if len(errors) < 20:
                errors.append(f'INDX-Block {i}: {exc}')
            continue
        for hint in parsed_hints:
            key = (hint.record, hint.sequence, hint.parent, hint.name.casefold())
            if key not in seen:
                seen.add(key)
                hints.append(hint)
    return hints
