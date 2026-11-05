"""Bounded read-only FAT32 allocation evidence for free-space carving.

Uses the low 28 bits of FAT entries, never FSInfo free-count hints. Mirrored
FATs must agree; without mirroring only the declared active FAT is used.
This is allocation evidence, not validation of every live directory/file chain.
"""
import hashlib
import struct

from .filesystems import FAT32, FileSystemError, ScanCancelled, read_exact

MAX_TABLE_BYTES = 128 * 1024**2
CHUNK_BYTES = 64 * 1024


class AllocationUnavailable(ValueError):
    pass


def _stop(cancel):
    if cancel and cancel():
        raise ScanCancelled('Scan abgebrochen.')


def free_fat32_ranges(stream, partition_offset, source_size, *, cancel=None,
                      max_table_bytes=MAX_TABLE_BYTES):
    """Return lazy absolute free ranges, byte count and metadata SHA256.

    Only genuine FAT32 geometry (at least 65525 data clusters) is accepted.
    A clean/unflagged table and an allocated root cluster are required.
    Metadata memory is bounded to a bitmap plus two 64-KiB table chunks.
    """
    _stop(cancel)
    try:
        volume = FAT32(stream, partition_offset)
        boot = read_exact(stream, partition_offset, 512)
        count = volume.cluster_count
        flags = int.from_bytes(boot[40:42], 'little')
        if (not 65525 <= count < 0x0ffffff5 or any(boot[17:21]) or any(boot[22:24]) or
                any(boot[42:44]) or flags & 0xff70 or
                boot[21] not in (0xf0, *range(0xf8, 0x100))):
            raise AllocationUnavailable('FAT32-Geometrie oder Versionsangaben nicht unterstützt.')
        if partition_offset + volume.total_sectors * volume.bps > source_size:
            raise AllocationUnavailable('FAT32-Volume reicht über das Image-Ende hinaus.')
        required = (count + 2) * 4
        copies = tuple(range(volume.fats)) if volume.mirroring_enabled else (volume.active_fat,)
        if required > volume.fat_bytes or required * len(copies) > max_table_bytes:
            raise AllocationUnavailable('FAT32-Belegungstabellen sind zu kurz oder überschreiten das Leselimit.')
        bitmap = bytearray((count + 7) // 8)
        digest = hashlib.sha256(boot)
        free = 0
        root_value = None
        for at in range(0, required, CHUNK_BYTES):
            _stop(cancel)
            size = min(CHUNK_BYTES, required-at)
            chunks = [read_exact(stream, volume.fat_offset + copy*volume.fat_bytes + at, size)
                      for copy in copies]
            for chunk in chunks:
                digest.update(chunk)
            values = [struct.iter_unpack('<I', chunk) for chunk in chunks]
            for index, row in enumerate(zip(*values), at//4):
                if index % 4096 == 0:
                    _stop(cancel)
                value = row[0][0] & 0x0fffffff
                if any((item[0] & 0x0fffffff) != value for item in row[1:]):
                    raise AllocationUnavailable('Gespiegelte FAT32-Belegungstabellen widersprechen sich.')
                if index == 0:
                    if value != (0x0fffff00 | boot[21]):
                        raise AllocationUnavailable('FAT32-Medienkennung in der Tabelle ist ungültig.')
                elif index == 1:
                    if value < 0x0ffffff8:
                        raise AllocationUnavailable('FAT32-Tabelle ist als unsauber oder mit E/A-Fehler markiert.')
                else:
                    if value and not (2 <= value < count+2 or value >= 0x0ffffff0):
                        raise AllocationUnavailable('FAT32-Verweis liegt außerhalb des Datenbereichs.')
                    cluster = index-2
                    if value:
                        bitmap[cluster//8] |= 1 << (cluster%8)
                    else:
                        free += 1
                    if index == volume.root_cluster:
                        root_value = value
        if root_value is None or not (2 <= root_value < count+2 or root_value >= 0x0ffffff8):
            raise AllocationUnavailable('FAT32-Stammverzeichnis ist nicht gültig zugeordnet.')
    except ScanCancelled:
        raise
    except (FileSystemError, OSError, ValueError) as exc:
        raise AllocationUnavailable(str(exc)) from exc

    data_start = volume.cluster_offset(2)
    def ranges():
        start = None
        for byte_index, value in enumerate(bitmap):
            if byte_index % 65536 == 0:
                _stop(cancel)
            first = byte_index * 8
            if value == 0 and first+8 <= count:
                if start is None:
                    start = first
                continue
            if value == 255 and start is None:
                continue
            for cluster in range(first, min(first+8, count)):
                if not value & (1 << (cluster-first)):
                    if start is None:
                        start = cluster
                elif start is not None:
                    yield data_start+start*volume.cluster_size, data_start+cluster*volume.cluster_size
                    start = None
        if start is not None:
            yield data_start+start*volume.cluster_size, data_start+count*volume.cluster_size
    return ranges, free*volume.cluster_size, digest.hexdigest()
