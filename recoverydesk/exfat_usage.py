"""Bounded read-only exFAT bitmap evidence for free-space carving.

One FAT/bitmap pair only. Validate both boot regions, bounded root/bitmap FAT
chains and allocation of those metadata clusters. Never infer free space from
FAT zeros or PercentInUse; exFAT FAT entries can remain after deletion.
"""
from array import array
import hashlib
import struct

from .filesystems import ExFAT, FileSystemError, ScanCancelled, read_exact

MAX_BITMAP_BYTES = 128 * 1024**2
MAX_ROOT_BYTES = 32 * 1024**2
MAX_METADATA_BYTES = 192 * 1024**2
MAX_CHAIN_CLUSTERS = 327680


class AllocationUnavailable(ValueError):
    pass


def _stop(cancel):
    if cancel and cancel():
        raise ScanCancelled('Scan abgebrochen.')


def _boot_region(region, sector_size):
    checksum = 0
    for offset, value in enumerate(memoryview(region)[:11*sector_size]):
        if offset not in (106,107,112):
            checksum = (((checksum & 1) << 31) + (checksum >> 1) + value) & 0xffffffff
    if any(value != checksum for (value,) in struct.iter_unpack('<I',region[11*sector_size:])):
        raise AllocationUnavailable('exFAT-Bootprüfsumme ist ungültig.')
    if any(region[10*sector_size:11*sector_size]):
        raise AllocationUnavailable('Reservierter exFAT-Bootbereich ist nicht leer.')
    for sector in range(1,9):
        if region[(sector+1)*sector_size-4:(sector+1)*sector_size] != b'\0\0\x55\xaa':
            raise AllocationUnavailable('Erweiterte exFAT-Bootsignatur ist ungültig.')
    normalized = bytearray(region[:11*sector_size])
    for offset in (106,107,112):
        normalized[offset] = 0
    return normalized


def free_exfat_ranges(stream, partition_offset, source_size, *, cancel=None,
                      max_bitmap_bytes=MAX_BITMAP_BYTES, max_root_bytes=MAX_ROOT_BYTES):
    """Return lazy absolute free ranges, byte count and fresh metadata SHA256."""
    _stop(cancel)
    digest = hashlib.sha256()
    inspected = 512  # ExFAT's bounded geometry probe reads one 512-byte header.
    try:
        volume = ExFAT(stream,partition_offset)
        end = partition_offset + volume.vol_sectors*volume.bps
        if end > source_size:
            raise AllocationUnavailable('exFAT-Volume reicht über das Image-Ende hinaus.')
        def read(at,size):
            nonlocal inspected
            _stop(cancel)
            if (at < partition_offset or size < 0 or at+size > end or
                    size > MAX_METADATA_BYTES-inspected):
                raise AllocationUnavailable('exFAT-Metadaten überschreiten Bereich oder Leselimit.')
            data = read_exact(stream,at,size)
            inspected += size
            digest.update(data)
            return data
        boot = read(partition_offset,512)
        flags = int.from_bytes(boot[106:108],'little')
        if volume.fat_count != 1 or flags & 1:
            raise AllocationUnavailable('exFAT-Freiraumsuche unterstützt nur eine FAT und eine Bitmap; kein TexFAT.')
        if (flags & 0xfff6 or boot[0:3] != b'\xeb\x76\x90' or any(boot[11:64]) or
                boot[104:106] != b'\0\x01' or any(boot[113:120]) or
                boot[112] not in (*range(101),255)):
            raise AllocationUnavailable('exFAT-Status oder Versionsangaben sind nicht unterstützt oder unsauber.')
        required = (volume.cluster_count+7)//8
        if required > max_bitmap_bytes or (volume.cluster_count+2)*4 > volume.fat_length*volume.bps:
            raise AllocationUnavailable('exFAT-Bitmap oder FAT überschreitet ihre sichere Größe.')
        main = read(partition_offset,12*volume.bps)
        backup = read(partition_offset+12*volume.bps,12*volume.bps)
        if _boot_region(main,volume.bps) != _boot_region(backup,volume.bps):
            raise AllocationUnavailable('exFAT-Bootkopien widersprechen sich.')
        if read(volume.fat_offset,8) != struct.pack('<II',0xfffffff8,0xffffffff):
            raise AllocationUnavailable('Reservierte exFAT-FAT-Einträge sind ungültig.')
        owned = set()
        def chain(first,limit,expected=None):
            result = array('I')
            current = first
            while current != 0xffffffff:
                _stop(cancel)
                if (not 2 <= current < volume.cluster_count+2 or current in owned or
                        len(result) >= limit or len(owned) >= MAX_CHAIN_CLUSTERS):
                    raise AllocationUnavailable('exFAT-Metadatenkette ist ungültig, überlappend oder zu lang.')
                owned.add(current);result.append(current)
                current = int.from_bytes(read(volume.fat_offset+current*4,4),'little')
            if not result or expected is not None and len(result) != expected:
                raise AllocationUnavailable('exFAT-Metadatenkette hat eine ungültige Länge.')
            return result
        root = chain(volume.root_cluster,max_root_bytes//volume.cluster_size)
        directory = bytearray()
        for cluster in root:
            directory.extend(read(volume.cluster_offset(cluster),volume.cluster_size))
        bitmaps = []
        for at in range(0,len(directory),32):
            if at % 65536 == 0:
                _stop(cancel)
            entry = memoryview(directory)[at:at+32]
            if entry[0] == 0:
                break
            if entry[0] == 0x81:
                if entry[1] != 0 or any(entry[2:20]):
                    raise AllocationUnavailable('exFAT-Bitmapkennung ist nicht eindeutig unterstützt.')
                bitmaps.append(struct.unpack_from('<IQ',entry,20))
        if len(bitmaps) != 1:
            raise AllocationUnavailable('Keine eindeutige aktive exFAT-Belegungsbitmap gefunden.')
        first,length = bitmaps[0]
        if not required <= length <= max_bitmap_bytes:
            raise AllocationUnavailable('exFAT-Belegungsbitmap ist zu kurz oder überschreitet das Leselimit.')
        count = (length+volume.cluster_size-1)//volume.cluster_size
        bitmap_chain = chain(first,count,expected=count)
        bitmap = bytearray()
        for cluster in bitmap_chain:
            bitmap.extend(read(volume.cluster_offset(cluster),min(volume.cluster_size,length-len(bitmap))))
        for index,cluster in enumerate(owned):
            if index % 4096 == 0:
                _stop(cancel)
            bit = cluster-2
            if not bitmap[bit//8] & (1 << (bit%8)):
                raise AllocationUnavailable('exFAT-Metadatencluster ist in der Bitmap als frei markiert.')
        used = 0
        for at in range(0,required-1,65536):
            _stop(cancel)
            used += sum(value.bit_count() for value in memoryview(bitmap)[at:min(at+65536,required-1)])
        used += (bitmap[required-1] & ((1 << (volume.cluster_count%8 or 8))-1)).bit_count()
    except ScanCancelled:
        raise
    except (FileSystemError,OSError,ValueError) as exc:
        raise AllocationUnavailable(str(exc)) from exc

    data_start = volume.cluster_offset(2)
    def ranges():
        start = None
        for byte_index,value in enumerate(memoryview(bitmap)[:required]):
            if byte_index % 65536 == 0:
                _stop(cancel)
            first = byte_index*8
            if value == 0 and first+8 <= volume.cluster_count:
                if start is None:start = first
                continue
            if value == 255 and start is None:continue
            for cluster in range(first,min(first+8,volume.cluster_count)):
                if not value & (1 << (cluster-first)):
                    if start is None:start = cluster
                elif start is not None:
                    yield data_start+start*volume.cluster_size,data_start+cluster*volume.cluster_size
                    start = None
        if start is not None:
            yield data_start+start*volume.cluster_size,data_start+volume.cluster_count*volume.cluster_size
    return ranges,(volume.cluster_count-used)*volume.cluster_size,digest.hexdigest()
