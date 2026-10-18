"""Conservative, read-only NTFS $MFT analysis for raw disk/volume images.

No file-system driver and no write operations to the source are used.
Supported recovery: intact deleted MFT records with resident or plain,
non-resident unnamed $DATA, including fragmented runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import struct
from typing import Callable, Iterator
from .sources import open_source, ensure_safe_destination, is_device_source


class NTFSError(ValueError):
    """Invalid/unsupported NTFS metadata or incomplete data."""


@dataclass(frozen=True)
class NTFSInfo:
    partition_offset: int
    bytes_per_sector: int
    sectors_per_cluster: int
    cluster_size: int
    total_sectors: int
    mft_lcn: int
    record_size: int

    @property
    def volume_size(self) -> int:
        return self.total_sectors * self.bytes_per_sector


@dataclass(frozen=True)
class DataRun:
    lcn: int | None  # None means sparse/zero-filled
    clusters: int


@dataclass
class NTFSFile:
    record_number: int
    name: str
    parent_record: int
    size: int
    is_deleted: bool
    data_kind: str
    data_runs: list[DataRun] = field(default_factory=list)
    resident_data: bytes | None = None
    initialized_size: int = 0
    unsupported_reason: str = ""

    @property
    def recoverable(self) -> bool:
        return not self.unsupported_reason and self.data_kind in ("resident", "nonresident")


def _u16(buf: bytes, pos: int) -> int:
    return struct.unpack_from("<H", buf, pos)[0]


def _u32(buf: bytes, pos: int) -> int:
    return struct.unpack_from("<I", buf, pos)[0]


def _u64(buf: bytes, pos: int) -> int:
    return struct.unpack_from("<Q", buf, pos)[0]


def _read_exact(f, offset: int, length: int) -> bytes:
    if offset < 0 or length < 0:
        raise NTFSError("Ungültiger Offset oder ungültige Länge.")
    f.seek(offset)
    result = f.read(length)
    if len(result) != length:
        raise NTFSError(f"Image unvollständig: {length} Bytes ab Offset {offset} benötigt, {len(result)} erhalten.")
    return result


def parse_boot_sector(f, partition_offset: int = 0) -> NTFSInfo:
    if partition_offset < 0 or partition_offset % 512 != 0:
        raise NTFSError("Der Partitions-Offset muss nichtnegativ und durch 512 teilbar sein.")
    b = _read_exact(f, partition_offset, 512)
    if b[3:11] != b"NTFS    " or b[510:512] != b"\x55\xaa":
        raise NTFSError("Kein gültiger NTFS-Bootsektor am angegebenen Partitions-Offset.")
    bps = _u16(b, 11)
    spc = b[13]
    sectors = _u64(b, 40)
    mft_lcn = _u64(b, 48)
    cpfr = struct.unpack_from("<b", b, 64)[0]
    if bps not in (512, 1024, 2048, 4096) or spc == 0 or spc & (spc - 1):
        raise NTFSError("Ungültige NTFS-Sektor- oder Clustergröße.")
    cluster_size = bps * spc
    if cluster_size > 2 * 1024 * 1024 or sectors == 0:
        raise NTFSError("Unplausible NTFS-Volumegröße.")
    record_size = cpfr * cluster_size if cpfr > 0 else (1 << -cpfr if cpfr < 0 else 0)
    if not 512 <= record_size <= 65536 or record_size % bps:
        raise NTFSError("Ungültige NTFS-MFT-Recordgröße.")
    if mft_lcn * cluster_size + record_size > sectors * bps:
        raise NTFSError("MFT liegt außerhalb des NTFS-Volumes.")
    return NTFSInfo(partition_offset, bps, spc, cluster_size, sectors, mft_lcn, record_size)


def apply_update_sequence(raw: bytes, sector_size: int) -> bytes:
    """Validate and apply NTFS fixups; reject torn/partially overwritten records."""
    if raw[:4] != b"FILE" or len(raw) < 48 or len(raw) % sector_size:
        raise NTFSError("Kein vollständiger MFT-FILE-Record.")
    usa_offset = _u16(raw, 4)
    usa_count = _u16(raw, 6)
    if usa_count != len(raw) // sector_size + 1 or usa_offset < 8 or usa_offset + 2 * usa_count > len(raw):
        raise NTFSError("Beschädigtes MFT-Update-Sequence-Array.")
    usn = raw[usa_offset:usa_offset+2]
    output = bytearray(raw)
    for i in range(1, usa_count):
        end = i * sector_size - 2
        if raw[end:end+2] != usn:
            raise NTFSError("MFT-Record besitzt einen beschädigten Sektor-Fixup.")
        output[end:end+2] = raw[usa_offset+i*2:usa_offset+i*2+2]
    return bytes(output)


def parse_runlist(blob: bytes, total_clusters: int) -> list[DataRun]:
    """Decode signed relative LCNs, respecting sparse runs and volume bounds."""
    runs: list[DataRun] = []
    pos, lcn = 0, 0
    for _ in range(1_000_000):
        if pos >= len(blob):
            raise NTFSError("NTFS-Runlist besitzt kein Endzeichen.")
        header = blob[pos]
        pos += 1
        if header == 0:
            return runs
        len_width = header & 15
        off_width = header >> 4
        if not 1 <= len_width <= 8 or off_width > 8 or pos + len_width + off_width > len(blob):
            raise NTFSError("Ungültige Runlist-Feldlänge.")
        clusters = int.from_bytes(blob[pos:pos+len_width], "little")
        pos += len_width
        if clusters == 0 or clusters > total_clusters:
            raise NTFSError("Ungültige Runlist-Clusteranzahl.")
        if off_width == 0:
            runs.append(DataRun(None, clusters))
        else:
            delta = int.from_bytes(blob[pos:pos+off_width], "little", signed=True)
            lcn += delta
            if lcn < 0 or lcn + clusters > total_clusters:
                raise NTFSError("Runlist zeigt außerhalb des NTFS-Volumes.")
            runs.append(DataRun(lcn, clusters))
            pos += off_width
    raise NTFSError("Zu viele Runlist-Abschnitte.")


def attributes(record: bytes):
    if len(record) < 48 or record[:4] != b"FILE":
        raise NTFSError("Kein gültiger FILE-Record.")
    pos = _u16(record, 20)
    if not 0x18 <= pos < len(record):
        raise NTFSError("Ungültiger Attribut-Offset im MFT-Record.")
    while pos + 8 <= len(record):
        kind = _u32(record, pos)
        if kind == 0xFFFFFFFF:
            return
        length = _u32(record, pos+4)
        if length < 24 or pos + length > len(record):
            raise NTFSError("Ungültige Attributlänge.")
        a = record[pos:pos+length]
        nonresident = a[8]
        name_len, name_off = a[9], _u16(a, 10)
        if name_len and (name_off < 24 or name_off + name_len*2 > len(a)):
            raise NTFSError("Beschädigter Attributname.")
        name = a[name_off:name_off+name_len*2].decode("utf-16le", "replace") if name_len else ""
        flags = _u16(a, 12)
        if nonresident == 0:
            value_len, value_off = _u32(a, 16), _u16(a, 20)
            if value_off < 24 or value_off + value_len > len(a):
                raise NTFSError("Beschädigter residenter Datenbereich.")
            yield kind, name, flags, False, a[value_off:value_off+value_len]
        elif nonresident == 1:
            if len(a) < 64:
                raise NTFSError("Unvollständiges non-residentes Attribut.")
            start_vcn, last_vcn = _u64(a, 16), _u64(a, 24)
            runs_offset = _u16(a, 32)
            real_size, init_size = _u64(a, 48), _u64(a, 56)
            if runs_offset < 64 or runs_offset >= len(a):
                raise NTFSError("Ungültiger Runlist-Offset.")
            yield kind, name, flags, True, (start_vcn, last_vcn, real_size, init_size, a[runs_offset:])
        else:
            raise NTFSError("Unbekannter Attributtyp resident/non-resident.")
        pos += length


def _best_name(filename_attrs: list[bytes]) -> tuple[str, int] | None:
    choices = []
    for value in filename_attrs:
        if len(value) < 66:
            continue
        length, namespace = value[64], value[65]
        if 66 + length * 2 > len(value) or length == 0:
            continue
        name = value[66:66+length*2].decode("utf-16le", "replace")
        parent = _u64(value, 0) & 0x0000FFFFFFFFFFFF
        priority = {3: 0, 1: 1, 0: 2, 2: 3}.get(namespace, 4)
        choices.append((priority, -len(name), name, parent))
    if not choices:
        return None
    _, _, name, parent = min(choices)
    return name, parent


def parse_file_record(raw: bytes, record_number: int, info: NTFSInfo) -> NTFSFile | None:
    record = apply_update_sequence(raw, info.bytes_per_sector)
    flags = _u16(record, 22)
    if flags & 1 or flags & 2:  # only deleted, non-directory records
        return None
    if _u64(record, 32) != 0:  # extension record, not base file record
        return None
    name_attrs, data_attrs = [], []
    attr_list = False
    for kind, name, attr_flags, nonresident, payload in attributes(record):
        if kind == 0x20:
            attr_list = True
        elif kind == 0x30 and not nonresident:
            name_attrs.append(payload)
        elif kind == 0x80 and name == "":
            data_attrs.append((attr_flags, nonresident, payload))
    preferred = _best_name(name_attrs)
    if not preferred:
        return None
    name, parent = preferred
    entry = NTFSFile(record_number, name, parent, 0, True, "none")
    if attr_list:
        entry.unsupported_reason = "Attributliste erfordert weitere MFT-Erweiterungsrecords"
    if len(data_attrs) != 1:
        entry.unsupported_reason = "Kein eindeutiger unbenannter NTFS-Datenstrom"
        return entry
    a_flags, nonresident, payload = data_attrs[0]
    if a_flags & 0xC001:
        entry.unsupported_reason = "Komprimierter, verschlüsselter oder Sparse-Datenstrom"
    if not nonresident:
        entry.data_kind = "resident"
        entry.resident_data = payload
        entry.size = entry.initialized_size = len(payload)
        return entry
    start_vcn, last_vcn, real_size, initialized_size, runblob = payload
    entry.data_kind = "nonresident"
    entry.size = real_size
    entry.initialized_size = initialized_size
    if start_vcn != 0:
        entry.unsupported_reason = "Fragmentierte Attributliste/fehlender erster VCN"
        return entry
    entry.data_runs = parse_runlist(runblob, info.total_sectors // info.sectors_per_cluster)
    total_covered = sum(run.clusters for run in entry.data_runs) * info.cluster_size
    if (real_size > total_covered or initialized_size > real_size or
            (entry.data_runs and last_vcn + 1 != sum(run.clusters for run in entry.data_runs))):
        entry.unsupported_reason = "Datenstrom-/Runlist-Länge ist inkonsistent"
    return entry


def iter_stream(f, info: NTFSInfo, runs: list[DataRun],
                offset: int, length: int, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    """Yield stream segments without loading an entire file into RAM."""
    if offset < 0 or length < 0 or chunk_size <= 0:
        raise NTFSError("Ungültiger Stream-Lesebereich.")
    end = offset + length
    current = 0
    delivered = 0
    for run in runs:
        run_size = run.clusters * info.cluster_size
        lo, hi = max(offset, current), min(end, current + run_size)
        if lo < hi:
            from_in_run = lo - current
            remaining = hi - lo
            while remaining:
                take = min(remaining, chunk_size)
                if run.lcn is None:
                    chunk = bytes(take)
                else:
                    raw_offset = info.partition_offset + run.lcn * info.cluster_size + from_in_run
                    if raw_offset + take > info.partition_offset + info.volume_size:
                        raise NTFSError("Datenstrom verweist außerhalb der Partition.")
                    chunk = _read_exact(f, raw_offset, take)
                yield chunk
                remaining -= take
                from_in_run += take
                delivered += take
        current += run_size
        if current >= end:
            break
    if delivered != length:
        raise NTFSError("Datei kann nicht vollständig aus den bekannten Clustern gelesen werden.")


def scan_deleted_files(image_path: str, partition_offset: int = 0,
                       max_records: int = 250_000,
                       progress: Callable[[int, int], None] | None = None
                       ) -> tuple[NTFSInfo, list[NTFSFile]]:
    """Examine free MFT base records for deleted files; does not alter image."""
    if not 1 <= max_records <= 10_000_000:
        raise ValueError("max_records außerhalb des zulässigen Bereichs.")
    results: list[NTFSFile] = []
    with open_source(image_path) as f:
        info = parse_boot_sector(f, partition_offset)
        first_raw = _read_exact(f, partition_offset + info.mft_lcn * info.cluster_size,
                                info.record_size)
        first = apply_update_sequence(first_raw, info.bytes_per_sector)
        if _u64(first, 32) != 0:
            raise NTFSError("MFT-Datensatz 0 ist unerwartet ein Erweiterungsrecord.")
        mft_streams = []
        mft_has_attr_list = False
        for kind, name, flags, nonresident, payload in attributes(first):
            if kind == 0x20:
                mft_has_attr_list = True
            elif kind == 0x80 and not name:
                mft_streams.append((flags, nonresident, payload))
        if mft_has_attr_list:
            raise NTFSError("$MFT hat eine Attributliste; Erweiterungs-Extents werden noch nicht unterstützt.")
        if len(mft_streams) != 1 or not mft_streams[0][1]:
            raise NTFSError("$MFT-Datenstrom ist nicht als einzelnes non-residentes Attribut verfügbar.")
        mft_flags, _, payload = mft_streams[0]
        start_vcn, last_vcn, mft_bytes, initialized_size, raw_runs = payload
        if start_vcn or mft_flags & 0xC001:
            raise NTFSError("Nicht unterstützter $MFT-Datenstrom.")
        runs = parse_runlist(raw_runs, info.total_sectors // info.sectors_per_cluster)
        if mft_bytes > sum(r.clusters for r in runs) * info.cluster_size:
            raise NTFSError("$MFT ist größer als seine Runlist.")
        count = min(max_records, mft_bytes // info.record_size)
        for rec_no in range(count):
            # Consume a single logical MFT record, including discontinuous MFT runs.
            try:
                raw = b"".join(iter_stream(f, info, runs, rec_no * info.record_size, info.record_size))
                if raw[:4] == b"FILE":
                    entry = parse_file_record(raw, rec_no, info)
                    if entry is not None:
                        results.append(entry)
            except NTFSError:
                # A damaged record should not abort analysis of other records.
                pass
            if progress and (rec_no % 512 == 0 or rec_no == count - 1):
                progress(rec_no+1, count)
    return info, results


def recover_ntfs_file(image_path: str, entry: NTFSFile, destination: str,
                      partition_offset: int = 0) -> int:
    """Export an intact stream, without overwriting an existing destination."""
    if not entry.is_deleted or not entry.recoverable:
        raise NTFSError(entry.unsupported_reason or "Dieser MFT-Eintrag ist nicht wiederherstellbar.")
    source = image_path if is_device_source(image_path) else os.path.realpath(image_path)
    target = os.path.realpath(destination)
    if os.path.normcase(source) == os.path.normcase(target):
        raise ValueError("Quelle und Zieldatei dürfen nicht identisch sein.")
    # Refuse symlinked existing destinations and all overwrites (open mode xb).
    if os.path.lexists(destination):
        raise FileExistsError("Die Zieldatei existiert bereits.")
    bytes_copied = 0
    ensure_safe_destination(source, target)
    with open_source(source) as f:
        info = parse_boot_sector(f, partition_offset)
        folder = os.path.dirname(os.path.abspath(destination))
        if not os.path.isdir(folder):
            raise FileNotFoundError("Der Zielordner existiert nicht.")
        created_by_us = False
        try:
            with open(destination, "xb", buffering=0) as dst:
                created_by_us = True
                if entry.data_kind == "resident":
                    data = entry.resident_data or b""
                    if len(data) != entry.size:
                        raise NTFSError("Residenter Datenstrom ist beschädigt.")
                    dst.write(data)
                    bytes_copied = len(data)
                else:
                    for chunk in iter_stream(f, info, entry.data_runs, 0, entry.initialized_size):
                        dst.write(chunk)
                        bytes_copied += len(chunk)
                    remaining = entry.size - entry.initialized_size
                    while remaining:
                        zeros = bytes(min(1024 * 1024, remaining))
                        dst.write(zeros)
                        bytes_copied += len(zeros)
                        remaining -= len(zeros)
                dst.flush()
                os.fsync(dst.fileno())
        except Exception:
            # Never leave a misleading partial recovery named as a complete file.
            if created_by_us and os.path.exists(destination):
                os.unlink(destination)
            raise
    return bytes_copied
