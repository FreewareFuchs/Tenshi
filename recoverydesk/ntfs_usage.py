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


def inspect_ntfs_bitmap(f, partition_offset: int, *, max_bitmap_bytes: int = MAX_BITMAP_BYTES) -> NTFSBitmapUsage:
    """Count used clusters via MFT system file #6; bounded memory and IO.

    Bitmap semantics: bit 1 = allocated cluster. Unused padding bits in the
    final byte are masked out. Returns capacity of *data clusters*, which
    can differ slightly from the NTFS total-sector count.
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

        # Only the valid cluster bits count, never the padding bits.
        counted = 0
        remaining = bitmap_required
        last_valid_bits = total_clusters % 8
        for chunk in chunks:
            if not chunk or len(chunk) > remaining:
                raise BitmapUnavailable('$Bitmap-Datenstrom besitzt eine ungültige Länge.')
            if remaining == len(chunk) and last_valid_bits:
                counted += sum(x.bit_count() for x in chunk[:-1])
                counted += (chunk[-1] & ((1 << last_valid_bits) - 1)).bit_count()
            else:
                counted += sum(x.bit_count() for x in chunk)
            remaining -= len(chunk)
        if remaining or counted > total_clusters:
            raise BitmapUnavailable('$Bitmap wurde nicht vollständig gelesen.')
        return NTFSBitmapUsage(total_clusters, counted, info.cluster_size)
    except (NTFSError, OSError, ValueError, OverflowError) as exc:
        raise BitmapUnavailable(str(exc)) from exc
