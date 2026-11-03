"""Read-only, bounded NTFS $Bitmap usage accounting.

Only counts allocation bits when the entire required bitmap can be read
through a verified, plain $MFT runlist. Nothing is written to the source.
"""
from __future__ import annotations

from dataclasses import dataclass
from .ntfs import (NTFSError, NTFSInfo, parse_boot_sector, apply_update_sequence,
                   parse_runlist, attributes, iter_stream, _read_exact)

# 128 MiB of $Bitmap covers 1,073,741,824 clusters, i.e. 4 TiB at 4 KiB.
MAX_BITMAP_BYTES = 128 * 1024 * 1024


class BitmapUnavailable(Exception):
    """Bitmap cannot be examined reliably; report unknown instead of guessing."""


@dataclass(frozen=True)
class NTFSBitmapUsage:
    clusters_total: int
    clusters_used: int
    cluster_size: int

    @property
    def used_bytes(self) -> int:
        return self.clusters_used * self.cluster_size

    @property
    def free_bytes(self) -> int:
        return (self.clusters_total - self.clusters_used) * self.cluster_size

    @property
    def capacity_bytes(self) -> int:
        return self.clusters_total * self.cluster_size


def _plain_unnamed_stream(record: bytes, total_clusters: int, name: str):
    streams = []
    has_attr_list = False
    for kind, attr_name, flags, nonresident, payload in attributes(record):
        if kind == 0x20:
            has_attr_list = True
        elif kind == 0x80 and not attr_name:
            streams.append((flags, nonresident, payload))
    if has_attr_list:
        raise BitmapUnavailable(f'{name} verwendet eine nicht unterstützte Attributliste.')
    if len(streams) != 1:
        raise BitmapUnavailable(f'{name} besitzt keinen eindeutigen $DATA-Strom.')
    flags, nonresident, payload = streams[0]
    if flags & 0xC001:
        raise BitmapUnavailable(f'{name} ist komprimiert, verschlüsselt oder sparsam gespeichert.')
    if not nonresident:
        return ('resident', payload, len(payload))
    start_vcn, last_vcn, real_size, initialized, encoded_runs = payload
    if start_vcn != 0 or initialized < real_size:
        raise BitmapUnavailable(f'{name} ist nicht vollständig initialisiert.')
    runs = parse_runlist(encoded_runs, total_clusters)
    if (any(r.lcn is None for r in runs) or
            last_vcn + 1 != sum(r.clusters for r in runs)):
        raise BitmapUnavailable(f'{name} hat eine unvollständige oder Sparse-Runlist.')
    return ('nonresident', runs, real_size)


def read_ntfs_bitmap(f, partition_offset: int, *, max_bitmap_bytes: int = MAX_BITMAP_BYTES, cancel=None, count_only=False):
    """Read allocation evidence via MFT system file #6; bounded memory and IO.

    Bitmap semantics: bit 1 = allocated cluster. Unused padding bits in the
    final byte are masked by callers. count_only retains the streaming usage
    calculation without allocating the full bitmap. The bitmap describes *data clusters*,
    whose capacity can differ slightly from the NTFS total-sector count.
    """
    try:
        info = parse_boot_sector(f, partition_offset)
        total_clusters = info.total_sectors // info.sectors_per_cluster
        bitmap_required = (total_clusters + 7) // 8
        if not total_clusters or bitmap_required > max_bitmap_bytes:
            raise BitmapUnavailable('NTFS-$Bitmap überschreitet das sichere Scanlimit.')
        mft0_raw = _read_exact(f, partition_offset + info.mft_lcn*info.cluster_size,
                               info.record_size)
        mft0 = apply_update_sequence(mft0_raw, info.bytes_per_sector)
        if int.from_bytes(mft0[32:40], 'little'):
            raise BitmapUnavailable('MFT-Basisdatensatz ist kein Basisrecord.')
        mft_kind, mft_stream, mft_len = _plain_unnamed_stream(mft0, total_clusters, '$MFT')
        if mft_kind != 'nonresident' or mft_len < info.record_size * 7:
            raise BitmapUnavailable('$MFT-Stream enthält nicht die Systemdatei $Bitmap.')
        bitmap_record_data = b''.join(iter_stream(
            f, info, mft_stream, 6 * info.record_size, info.record_size,
            chunk_size=info.record_size))
        bitmap_record = apply_update_sequence(bitmap_record_data, info.bytes_per_sector)
        # File record #6 is the NTFS special system file $Bitmap.
        if int.from_bytes(bitmap_record[32:40], 'little'):
            raise BitmapUnavailable('$Bitmap-Datensatz ist kein Basisrecord.')
        flags = int.from_bytes(bitmap_record[22:24], 'little')
        if not flags & 1 or flags & 2:
            raise BitmapUnavailable('$Bitmap-Systemdatei ist nicht als aktive Datei markiert.')
        # Verify the NTFS reserved record identity whenever its filename
        # attribute is available. Never interpret a different record's data
        # as an allocation bitmap.
        names = []
        for attr_type, attr_name, attr_flags, nonresident, attr_payload in attributes(bitmap_record):
            if attr_type != 0x30 or nonresident or len(attr_payload) < 66:
                continue
            name_len = attr_payload[64]
            if name_len and 66 + name_len * 2 <= len(attr_payload):
                names.append(attr_payload[66:66+name_len*2].decode('utf-16le', 'replace'))
        if names and '$Bitmap' not in names:
            raise BitmapUnavailable('MFT-Datensatz 6 hat nicht den erwarteten Namen $Bitmap.')
        kind, payload, real_size = _plain_unnamed_stream(bitmap_record, total_clusters, '$Bitmap')
        if real_size < bitmap_required:
            raise BitmapUnavailable('$Bitmap ist kürzer als die Volume-Clusteranzahl.')

        if kind == 'resident':
            chunks = (payload[:bitmap_required],)
        else:
            chunks = iter_stream(f, info, payload, 0, bitmap_required,
                                 chunk_size=1024 * 1024)

        # Retain bounded evidence for counting and lazy free-range iteration.
        result = bytearray()
        used = 0
        remaining = bitmap_required
        for chunk in chunks:
            if cancel and cancel():
                from .filesystems import ScanCancelled
                raise ScanCancelled('Scan abgebrochen.')
            if not chunk or len(chunk) > remaining:
                raise BitmapUnavailable('$Bitmap-Datenstrom besitzt eine ungültige Länge.')
            if count_only:
                if remaining == len(chunk) and total_clusters % 8:
                    used += sum(x.bit_count() for x in memoryview(chunk)[:-1])
                    used += (chunk[-1] & ((1 << (total_clusters % 8))-1)).bit_count()
                else:
                    used += sum(x.bit_count() for x in chunk)
            else:
                result.extend(chunk)
            remaining -= len(chunk)
        if remaining:
            raise BitmapUnavailable('$Bitmap wurde nicht vollständig gelesen.')
        return info, used if count_only else bytes(result)
    except (NTFSError, OSError, ValueError, OverflowError) as exc:
        raise BitmapUnavailable(str(exc)) from exc


def inspect_ntfs_bitmap(f, partition_offset: int, *, max_bitmap_bytes: int = MAX_BITMAP_BYTES) -> NTFSBitmapUsage:
    info, used = read_ntfs_bitmap(f, partition_offset, max_bitmap_bytes=max_bitmap_bytes,count_only=True)
    total = info.total_sectors // info.sectors_per_cluster
    return NTFSBitmapUsage(total, used, info.cluster_size)


def free_ntfs_ranges(f, partition_offset, source_size, *, cancel=None):
    """Return fresh, bounded bitmap evidence and lazy absolute free extents."""
    import hashlib
    info, bitmap = read_ntfs_bitmap(f, partition_offset, cancel=cancel)
    total = info.total_sectors // info.sectors_per_cluster
    if partition_offset + info.total_sectors * info.bytes_per_sector > source_size:
        raise BitmapUnavailable('NTFS-Volume reicht über das Image-Ende hinaus.')
    used = sum(x.bit_count() for x in memoryview(bitmap)[:-1])
    used += (bitmap[-1] & ((1 << (total % 8 or 8)) - 1)).bit_count()
    def ranges():
        start = None
        for byte_index, value in enumerate(bitmap):
            if byte_index % 65536 == 0 and cancel and cancel():
                from .filesystems import ScanCancelled
                raise ScanCancelled('Scan abgebrochen.')
            first = byte_index * 8
            if value == 0 and first + 8 <= total:
                if start is None:start = first
                continue
            if value == 255 and start is None:continue
            for cluster in range(first, min(first+8,total)):
                if not value & (1 << (cluster-first)):
                    if start is None:start = cluster
                elif start is not None:
                    yield partition_offset+start*info.cluster_size, partition_offset+cluster*info.cluster_size
                    start = None
        if start is not None:
            yield partition_offset+start*info.cluster_size, partition_offset+total*info.cluster_size
    return ranges, (total-used)*info.cluster_size, hashlib.sha256(bitmap).hexdigest()
