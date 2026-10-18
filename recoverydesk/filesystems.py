"""Read-only FAT32, exFAT and ext2/3/4 directory browsing and cautious recovery.

Deleted candidates are inherently uncertain; free clusters may contain reused data.
Forensic limitations: no replayed journals, no guaranteed deleted-file reconstruction,
no EFS/Unix encryption/compression decoding, no exotic exFAT TexFAT, no fsck.
Only in-use directory entries supported. The source is never modified.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import os
import struct
from typing import Callable, Iterator

from .sources import open_source, ensure_safe_destination, source_size, is_device_source
from .ntfs_browser import ExportReport, safe_name
from .export_io import write_chunks, ExportCancelled

ROOT = 5
MAX_ENTRIES = 300_000
MAX_FILE_SIZE = 16 * 1024**4

class FileSystemError(ValueError):
    pass

class ScanCancelled(FileSystemError):
    pass


def u16(b, o=0): return struct.unpack_from('<H', b, o)[0]
def u32(b, o=0): return struct.unpack_from('<I', b, o)[0]
def u64(b, o=0): return struct.unpack_from('<Q', b, o)[0]


def read_exact(f, where, n):
    if where < 0 or n < 0 or n > 16*1024*1024:
        raise FileSystemError('Ungültiger Leseauftrag')
    f.seek(where)
    data = f.read(n)
    if len(data) != n:
        raise FileSystemError(f'Image unvollständig bei Offset {where} ({n} Bytes)')
    return data


@dataclass
class GenericEntry:
    record_number: int
    name: str
    parent_record: int
    is_directory: bool
    size: int
    locator: tuple
    is_deleted: bool = False
    unsupported_reason: str = ''
    link_index: int = 0
    @property
    def key(self): return f'{self.record_number}:{self.link_index}'
    @property
    def recoverable(self): return not self.is_directory and not self.unsupported_reason
    @property
    def status(self):
        if self.is_deleted: return 'Gelöscht · unsicher' if self.recoverable else 'Gelöscht · nur Hinweis'
        return 'Vorhanden' if not self.unsupported_reason else 'Eingeschränkt'


@dataclass
class GenericIndex:
    filesystem: str
    offset: int
    entries: list[GenericEntry]
    volumes: object
    children: dict[int, list[GenericEntry]] = field(default_factory=dict)
    total_records: int = 0
    scanned_records: int = 0
    orphan_count: int = 0
    root: int = ROOT
    unreadable_directories: int = 0
    scan_warnings: list[str] = field(default_factory=list)
    tolerant: bool = False
    def list_dir(self, parent: int, show_deleted: bool = True):
        return sorted([e for e in self.children.get(parent, ()) if show_deleted or not e.is_deleted],
                      key=lambda e: (not e.is_directory, e.name.casefold(), e.record_number))
    def preview(self, source: str, entry: GenericEntry, maximum: int = 65536):
        with open_source(source) as f:
            return b''.join(self.volumes.iter_file(f, entry, max_bytes=maximum))


class VolumeBase:
    def __init__(self, offset: int):
        self.offset = offset
    def iter_file(self, f, entry: GenericEntry, max_bytes: int | None = None) -> Iterator[bytes]:
        raise NotImplementedError
    def list_directory(self, f, locator: tuple):
        raise NotImplementedError


class FAT32(VolumeBase):
    label = 'FAT32'
    def __init__(self, f, offset):
        super().__init__(offset)
        b = read_exact(f, offset, 512)
        if b[82:90] != b'FAT32   ' or b[510:512] != b'\x55\xaa':
            raise FileSystemError('Kein FAT32-Bootsektor an dieser Position')
        self.bps = u16(b, 11)
        self.spc = b[13]
        self.reserved = u16(b, 14)
        self.fats = b[16]
        self.fat_sectors = u32(b, 36)
        self.total_sectors = u32(b, 32) or u16(b, 19)
        self.root_cluster = u32(b, 44)
        if (self.bps not in (512,1024,2048,4096) or self.spc == 0 or
            self.spc & (self.spc-1) or self.spc > 128 or
            self.reserved < 1 or self.fats not in (1,2) or
            self.fat_sectors == 0 or self.root_cluster < 2):
            raise FileSystemError('Unplausible FAT32-Geometrie')
        self.cluster_size = self.bps*self.spc
        self.data_sector = self.reserved + self.fats * self.fat_sectors
        if self.data_sector >= self.total_sectors:
            raise FileSystemError('FAT32-Datenbereich außerhalb des Volumes')
        self.cluster_count = (self.total_sectors-self.data_sector)//self.spc
        if self.root_cluster >= self.cluster_count+2:
            raise FileSystemError('FAT32-Rootcluster außerhalb des Volumes')
        self.fat_offset = offset+self.reserved*self.bps
        self.fat_bytes = self.fat_sectors*self.bps
        # A stale second FAT can occasionally retain an old chain after the
        # first FAT was cleared. Only use it when FAT mirroring was enabled.
        self.mirroring_enabled = not bool(u16(b, 40) & 0x0080)

    def cluster_offset(self, cluster):
        if not 2 <= cluster < self.cluster_count+2:
            raise FileSystemError(f'Ungültiger FAT32-Cluster: {cluster}')
        return self.offset+(self.data_sector+(cluster-2)*self.spc)*self.bps

    def clusters(self, f, start):
        seen = set()
        current = start
        while 2 <= current < 0x0FFFFFF8:
            if current in seen or len(seen)>self.cluster_count:
                raise FileSystemError('Zyklische FAT32-Clusterkette')
            seen.add(current)
            self.cluster_offset(current)
            yield current
            fat_entry = current*4
            if fat_entry+4 > self.fat_bytes:
                raise FileSystemError('FAT32-Cluster außerhalb der FAT')
            current = u32(read_exact(f, self.fat_offset+fat_entry, 4)) & 0x0FFFFFFF
            if current in (0,1,0x0FFFFFF7):
                raise FileSystemError('FAT32-Kette enthält ungültigen oder defekten Cluster')

    def _bytes(self, f, cluster, size, max_bytes=None):
        remaining = min(size, max_bytes) if max_bytes is not None else size
        for c in self.clusters(f, cluster):
            if remaining == 0: return
            data = read_exact(f, self.cluster_offset(c), min(remaining, self.cluster_size))
            yield data
            remaining -= len(data)
        if remaining:
            raise FileSystemError('FAT32-Datei größer als ihre Clusterkette')

    def iter_file(self, f, entry, max_bytes=None):
        size = entry.size
        if size > MAX_FILE_SIZE: raise FileSystemError('Datei zu groß')
        if size == 0: return
        start = entry.locator[0]
        if start < 2: raise FileSystemError('Keine gültige Clusterzuordnung')
        if entry.is_deleted:
            # Never silently switch to a different recovery hypothesis after a
            # scan. Revalidate allocation state and the exact saved chain.
            mirror_chain = entry.locator[2] if len(entry.locator) > 2 and entry.locator[1] == 'mirror' else None
            if mirror_chain is not None:
                current = self._deleted_mirror_chain(f, start, size)
                if current is None or current != mirror_chain:
                    raise FileSystemError('FAT32-Spiegelkette verändert oder Cluster wiederbelegt')
                chosen = current
            else:
                if not self.deleted_range_is_free(f, start, size):
                    raise FileSystemError('Gelöschter FAT32-Bereich ist belegt oder nicht prüfbar')
                needed_clusters = (size + self.cluster_size - 1) // self.cluster_size
                chosen = range(start, start + needed_clusters)
            remaining = min(size, max_bytes) if max_bytes is not None else size
            for c in chosen:
                if remaining <= 0: break
                data = read_exact(f, self.cluster_offset(c), min(self.cluster_size, remaining))
                remaining -= len(data)
                yield data
            if remaining:
                raise FileSystemError('Gelöschte FAT32-Clusterfolge unvollständig')
            return
        yield from self._bytes(f, start, size, max_bytes)

    def deleted_range_is_free(self, f, cluster, size):
        # A best-effort contiguous hypothesis, NEVER proof of intact old content.
        needed = (size + self.cluster_size - 1) // self.cluster_size
        if needed < 0 or needed > min(self.cluster_count, 65536) or cluster < 2 or cluster + needed > self.cluster_count+2:
            return False
        for c in range(cluster, cluster+needed):
            where = c * 4
            if where+4 > self.fat_bytes:
                return False
            # Refuse recovery if the primary and mirror FAT disagree.
            for fat_copy in range(self.fats):
                fat_pos = self.fat_offset + fat_copy*self.fat_bytes + where
                if u32(read_exact(f, fat_pos, 4)) & 0x0FFFFFFF:
                    return False
        return True

    def _deleted_mirror_chain(self, f, start, size):
        """Find a *candidate* old FAT chain in a stale second FAT.

        It is never evidence of intact contents. FAT 0 must mark EVERY cluster
        free, all links in FAT 1 must be valid and the final link must be EOC.
        Disabled FAT mirroring, missing mirrors, cycles and oversized chains
        are rejected. The candidate is rechecked before every export.
        """
        if self.fats != 2 or not self.mirroring_enabled or size <= 0:
            return None
        count = (size + self.cluster_size - 1) // self.cluster_size
        if count < 2 or count > min(65536, self.cluster_count):
            return None
        seen = set()
        chain = []
        current = start
        for i in range(count):
            if current in seen or not 2 <= current < self.cluster_count + 2:
                return None
            where = current * 4
            if where + 4 > self.fat_bytes:
                return None
            if u32(read_exact(f, self.fat_offset + where, 4)) & 0x0FFFFFFF:
                return None  # new allocation in the authoritative first FAT
            next_value = u32(read_exact(f, self.fat_offset + self.fat_bytes + where, 4)) & 0x0FFFFFFF
            chain.append(current)
            seen.add(current)
            if i == count - 1:
                if not 0x0FFFFFF8 <= next_value <= 0x0FFFFFFF:
                    return None
            elif not 2 <= next_value < self.cluster_count + 2:
                return None
            current = next_value
        return tuple(chain)

    def list_directory(self, f, locator):
        cluster = locator[0]
        if cluster < 2: return []
        # Read up to 64 MiB directory content, prevent unbounded damaged chains.
        content = bytearray()
        for c in self.clusters(f, cluster):
            content.extend(read_exact(f, self.cluster_offset(c), self.cluster_size))
            if len(content) >= 64*1024*1024:
                raise FileSystemError('FAT32-Verzeichnis >64 MiB, Scan begrenzt')
            if any(content[i] == 0 for i in range(max(0,len(content)-self.cluster_size), len(content), 32)):
                break
        rows=[]
        lfn=[]
        for i in range(0, len(content)-31, 32):
            e=content[i:i+32]
            if e[0]==0: break
            deleted = e[0] == 0xE5
            if e[11] == 0x0F:
                if deleted:
                    lfn.clear()  # Original LFN sequence number was erased.
                    continue
                order=e[0] & 0x1F
                units=e[1:11]+e[14:26]+e[28:32]
                if order:
                    lfn.append((order,e[13],bytes(units)))
                continue
            if e[11] & 0x08:
                lfn.clear(); continue
            cluster_id=(u16(e,20)<<16)|u16(e,26)
            size=u32(e,28)
            directory=bool(e[11]&0x10)
            shortbase=(b'?' + e[1:8] if deleted else e[:8]).decode('cp437','replace').rstrip()
            ext=e[8:11].decode('cp437','replace').rstrip()
            shortname=shortbase+('.'+ext if ext else '')
            name=shortname
            if lfn and not deleted:
                checksum=0
                for byte in e[:11]:
                    checksum=((checksum&1)<<7)+(checksum>>1)+byte
                    checksum &=255
                if all(check==checksum for _,check,_ in lfn) and sorted(x[0] for x in lfn)==list(range(1,len(lfn)+1)):
                    raw=b''.join(fragment for _,_,fragment in sorted(lfn))
                    name=raw.decode('utf-16le','replace').split('\x00')[0].rstrip('\uffff')
            lfn.clear()
            if name in ('.','..') or not name:
                continue
            unsupported='' if directory or size==0 or cluster_id>=2 else 'Datei ohne gültigen Startcluster'
            entry_locator = (cluster_id,)
            if deleted:
                if directory:
                    unsupported = 'Gelöschter FAT32-Ordner: Clusterkette nicht sicher rekonstruierbar'
                elif size:
                    try:
                        mirror_chain = self._deleted_mirror_chain(f, cluster_id, size)
                    except (OSError, FileSystemError, struct.error):
                        mirror_chain = None
                    if mirror_chain is not None:
                        entry_locator = (cluster_id, 'mirror', mirror_chain)
                    elif not self.deleted_range_is_free(f, cluster_id, size):
                        unsupported = 'Freigegebene FAT32-Cluster sind bereits belegt oder nicht plausibel'
            rows.append((name,directory,size,entry_locator,unsupported,deleted))
        return rows


class ExFAT(VolumeBase):
    label='exFAT'
    def __init__(self,f,offset):
        super().__init__(offset)
        b=read_exact(f,offset,512)
        if b[3:11]!=b'EXFAT   ' or b[510:512]!=b'\x55\xaa':
            raise FileSystemError('Kein exFAT-Bootsektor an dieser Position')
        shift=b[108]; cshift=b[109]
        if shift not in (9,10,11,12) or cshift>20-shift:
            raise FileSystemError('Ungültige exFAT-Sektor/Clustergröße')
        self.bps=1<<shift
        self.spc=1<<cshift
        self.cluster_size=self.bps*self.spc
        self.vol_sectors=u64(b,72)
        self.fat_start=u32(b,80)
        self.fat_length=u32(b,84)
        self.heap_start=u32(b,88)
        self.cluster_count=u32(b,92)
        self.root_cluster=u32(b,96)
        self.fat_count=b[110]
        if (self.fat_count not in (1,2) or self.fat_start<24 or self.fat_length==0 or
            self.cluster_count==0 or self.cluster_count>0xFFFFFFF0 or
            self.heap_start<=self.fat_start or
            self.heap_start+self.cluster_count*self.spc>self.vol_sectors or
            not 2<=self.root_cluster<self.cluster_count+2):
            raise FileSystemError('Unplausible exFAT-Volumegeometrie')
        self.fat_offset=self.offset+self.fat_start*self.bps
        self._bitmap = None
        self._bitmap_cache = {}

    def _bitmap_free(self, f, start, size):
        """Check the exFAT allocation bitmap for a hypothesized contiguous deleted stream.

        A free bit does not prove old bytes are intact. Missing bitmap => refuse.
        """
        if size == 0: return True
        if self._bitmap is None or start < 2:
            return False
        bitmap_start, bitmap_size = self._bitmap
        count = (size + self.cluster_size - 1) // self.cluster_size
        if count > min(self.cluster_count, 65536) or start+count > self.cluster_count+2:
            return False
        for cluster in range(start, start+count):
            bit_index = cluster-2
            byte_index = bit_index//8
            if byte_index >= bitmap_size:
                return False
            bitmap_cluster_idx = byte_index//self.cluster_size
            if bitmap_cluster_idx not in self._bitmap_cache:
                # The bitmap can have a FAT chain; bounded lookup.
                if bitmap_cluster_idx > 1048576:
                    return False
                found = None
                for i,c in enumerate(self.clusters(f,bitmap_start)):
                    if i == bitmap_cluster_idx:
                        found = c
                        break
                    if i > bitmap_cluster_idx: break
                if found is None: return False
                self._bitmap_cache[bitmap_cluster_idx] = found
            physical = self.cluster_offset(self._bitmap_cache[bitmap_cluster_idx]) + byte_index%self.cluster_size
            value = read_exact(f,physical,1)[0]
            if value & (1 << (bit_index % 8)):
                return False
        return True

    def _bitmap_clusters_free(self, f, clusters):
        """Check precisely the clusters in a possibly fragmented deleted file."""
        if self._bitmap is None:
            return False
        bitmap_start, bitmap_size = self._bitmap
        if len(clusters) > min(65536, self.cluster_count):
            return False
        for cluster in clusters:
            if not 2 <= cluster < self.cluster_count + 2:
                return False
            bit_index = cluster - 2
            byte_index = bit_index // 8
            if byte_index >= bitmap_size:
                return False
            bitmap_cluster_idx = byte_index // self.cluster_size
            if bitmap_cluster_idx not in self._bitmap_cache:
                found = None
                for i, c in enumerate(self.clusters(f, bitmap_start)):
                    if i == bitmap_cluster_idx:
                        found = c
                        break
                    if i > bitmap_cluster_idx:
                        break
                if found is None:
                    return False
                self._bitmap_cache[bitmap_cluster_idx] = found
            physical = self.cluster_offset(self._bitmap_cache[bitmap_cluster_idx]) + byte_index % self.cluster_size
            if read_exact(f, physical, 1)[0] & (1 << (bit_index % 8)):
                return False
        return True

    def _deleted_fat_chain(self, f, start, size):
        """Return a bounded preserved exFAT chain when all bitmap bits are free.

        A deleted, FAT-chained stream (NoFatChain flag = 0) may retain its FAT
        pointers even though its allocation bits have been cleared. We refuse
        missing, broken, cyclic and overlong chains, and require the final EOC.
        """
        count = (size + self.cluster_size - 1) // self.cluster_size
        if not 1 <= count <= min(65536, self.cluster_count) or start < 2:
            return None
        chain = []
        seen = set()
        current = start
        for i in range(count):
            if current in seen or not 2 <= current < self.cluster_count + 2:
                return None
            if current*4+4 > self.fat_length*self.bps:
                return None
            seen.add(current)
            chain.append(current)
            nxt = u32(read_exact(f, self.fat_offset+current*4, 4))
            if i == count - 1:
                if not 0xFFFFFFF8 <= nxt <= 0xFFFFFFFF:
                    return None
            elif not 2 <= nxt < self.cluster_count + 2:
                return None
            current = nxt
        candidate = tuple(chain)
        if not self._bitmap_clusters_free(f, candidate):
            return None
        return candidate

    def cluster_offset(self,c):
        if not 2<=c<self.cluster_count+2:
            raise FileSystemError(f'Ungültiger exFAT-Cluster {c}')
        return self.offset+(self.heap_start+(c-2)*self.spc)*self.bps

    def clusters(self,f,start,contiguous=False,count=None):
        if contiguous:
            if count is None or count>self.cluster_count:
                raise FileSystemError('Ungültige zusammenhängende Clusteranzahl')
            for c in range(start,start+count):
                self.cluster_offset(c)
                yield c
            return
        current=start; seen=set()
        while 2<=current<0xFFFFFFF8:
            if current in seen or len(seen)>self.cluster_count:
                raise FileSystemError('Zyklische exFAT-Kette')
            seen.add(current);self.cluster_offset(current);yield current
            if current*4+4>self.fat_length*self.bps:
                raise FileSystemError('exFAT-Eintrag außerhalb der FAT')
            current=u32(read_exact(f,self.fat_offset+current*4,4))
            if current in (0,1,0xFFFFFFF7):
                raise FileSystemError('Defekte exFAT-Clusterkette')

    def _bytes(self,f,start,size,contiguous,max_bytes=None,unknown_dir=False):
        remaining=min(size,max_bytes) if max_bytes is not None else size
        if remaining==0:return
        count=(size+self.cluster_size-1)//self.cluster_size if contiguous else None
        for c in self.clusters(f,start,contiguous,count):
            if remaining<=0: return
            data=read_exact(f,self.cluster_offset(c),min(self.cluster_size,remaining))
            yield data
            remaining-=len(data)
        if remaining: raise FileSystemError('exFAT-Clusterkette kürzer als Datenlänge')

    def iter_file(self,f,entry,max_bytes=None):
        size=entry.size
        if size>MAX_FILE_SIZE: raise FileSystemError('Dateigröße nicht plausibel')
        if size:
            start, contiguous=entry.locator[:2]
            if entry.is_deleted:
                # Bitmap cluster locations are cached during directory browsing;
                # refresh them before export to detect changed bitmap FAT links.
                self._bitmap_cache.clear()
                if not contiguous:
                    saved_chain = entry.locator[3] if len(entry.locator) > 3 else None
                    current_chain = self._deleted_fat_chain(f, start, size)
                    if saved_chain is None or current_chain is None or saved_chain != current_chain:
                        raise FileSystemError('Gelöschte exFAT-FAT-Kette verändert oder Cluster nicht frei')
                    remaining = min(size, max_bytes) if max_bytes is not None else size
                    for cluster in current_chain:
                        if remaining <= 0: break
                        data = read_exact(f, self.cluster_offset(cluster), min(remaining, self.cluster_size))
                        remaining -= len(data)
                        yield data
                    if remaining:
                        raise FileSystemError('exFAT-Wiederherstellung unvollständig')
                    return
                if not self._bitmap_free(f, start, size):
                    raise FileSystemError('Gelöschte exFAT-Datencluster sind nicht verifiziert frei')
            yield from self._bytes(f,start,size,contiguous,max_bytes)

    def list_directory(self,f,locator):
        start,contiguous,size=locator
        if size is None:
            # Root cluster chain size unknown; stop at first 0x00 end marker.
            raw=bytearray()
            for c in self.clusters(f,start):
                raw.extend(read_exact(f,self.cluster_offset(c),self.cluster_size))
                if any(raw[k]==0 for k in range(len(raw)-self.cluster_size,len(raw),32)):
                    break
                if len(raw)>=64*1024*1024:
                    raise FileSystemError('exFAT-Wurzelverzeichnis >64 MiB')
        else:
            if size>64*1024*1024: raise FileSystemError('exFAT-Verzeichnis >64 MiB')
            raw=b''.join(self._bytes(f,start,size,contiguous)) if size else b''
        # The allocation bitmap lives in the root directory (entry type 0x81).
        if start == self.root_cluster:
            bitmaps = []
            for k in range(0,len(raw)-31,32):
                if raw[k] == 0x81:
                    bitmap_start = u32(raw,k+20)
                    bitmap_size = u64(raw,k+24)
                    if 2 <= bitmap_start < self.cluster_count+2 and 0 < bitmap_size <= (self.cluster_count+7)//8:
                        bitmaps.append((bitmap_start, bitmap_size))
            # TexFAT/ambiguous multiple bitmaps: do not guess the active one.
            self._bitmap = bitmaps[0] if len(bitmaps) == 1 else None
        rows=[]; i=0
        while i+32<=len(raw):
            first=raw[i]
            if first==0:break
            deleted = first == 0x05
            if first not in (0x85,0x05):
                i+=32;continue
            secondaries=raw[i+1]
            if secondaries<2 or secondaries>19 or i+(secondaries+1)*32>len(raw):
                i+=32;continue
            group=[raw[i+k*32:i+(k+1)*32] for k in range(secondaries+1)]
            i+=(secondaries+1)*32
            stream=next((s for s in group[1:] if s[0]==(0x40 if deleted else 0xC0)),None)
            names=[s for s in group[1:] if s[0]==(0x41 if deleted else 0xC1)]
            if stream is None:continue
            name_len=stream[3]
            name_raw=b''.join(s[2:32] for s in names)
            if not name_len or name_len>255 or len(name_raw)<name_len*2:
                continue
            name=name_raw[:name_len*2].decode('utf-16le','replace')
            directory=bool(u16(group[0],4)&0x10)
            start_cluster=u32(stream,20)
            data_len=u64(stream,24)
            valid_len=u64(stream,8)
            contiguous=bool(stream[1]&0x02)
            unsupported=''
            if data_len>MAX_FILE_SIZE or valid_len>data_len:
                unsupported='Ungültige exFAT-Datenlänge'
            if data_len and not (2<=start_cluster<self.cluster_count+2):
                unsupported='Ungültiger exFAT-Startcluster'
            recovery_chain = None
            if deleted:
                if directory:
                    unsupported = 'Gelöschter exFAT-Ordner: Clusterzuordnung ungesichert'
                elif data_len and valid_len != data_len:
                    unsupported = 'Gelöschte exFAT-Datei mit nicht vollständig initialisiertem Datenbereich'
                elif data_len and not contiguous:
                    try:
                        recovery_chain = self._deleted_fat_chain(f, start_cluster, data_len)
                    except (OSError, FileSystemError, struct.error):
                        recovery_chain = None
                    if recovery_chain is None:
                        unsupported = 'Gelöschte exFAT-FAT-Kette fehlt, ist beschädigt oder Bitmap nicht frei'
                elif data_len and not self._bitmap_free(f,start_cluster,data_len):
                    unsupported = 'Gelöschte exFAT-Cluster nicht nachweislich frei (Bitmap)'
            loc = ((start_cluster,contiguous,data_len,recovery_chain)
                   if recovery_chain is not None else
                   (start_cluster,contiguous,data_len))
            rows.append((name,directory,data_len,loc,unsupported,deleted))
        return rows


class Ext(VolumeBase):
    label='ext'
    def __init__(self,f,offset):
        super().__init__(offset)
        s=read_exact(f,offset+1024,1024)
        if u16(s,56)!=0xEF53:
            raise FileSystemError('Kein ext2/3/4-Superblock an dieser Position')
        self.inodes_count=u32(s,0)
        self.blocks_count=u32(s,4)
        log_block=u32(s,24)
        if log_block>6:raise FileSystemError('Ungültige ext-Blockgröße')
        self.block_size=1024<<log_block
        self.blocks_per_group=u32(s,32)
        self.inodes_per_group=u32(s,40)
        self.inode_size=u16(s,88) or 128
        self.first_data_block=u32(s,20)
        self.compat=u32(s,92)
        self.incompat=u32(s,96)
        self.ro_compat=u32(s,100)
        self.descriptor_size=u16(s,254) if (self.incompat&0x80) else 32
        if (self.inodes_count<2 or self.blocks_count<2 or self.blocks_per_group==0 or
            self.inodes_per_group==0 or self.inode_size<128 or self.inode_size>self.block_size or
            self.descriptor_size<32 or self.descriptor_size>1024 or self.descriptor_size%8):
            raise FileSystemError('Unplausible ext-Superblockwerte')
        if self.incompat&0x80:
            self.blocks_count |= u32(s,0x150)<<32
        self.group_count=(self.inodes_count+self.inodes_per_group-1)//self.inodes_per_group
        if self.group_count>1000000:raise FileSystemError('Zu viele ext-Blockgruppen')
        self.label='ext4' if self.incompat & (0x40|0x80|0x200) else ('ext3' if self.compat&4 else 'ext2')
        self.descriptor_offset=self.offset+(2*self.block_size if self.block_size==1024 else self.block_size)
        self._inode_table_cache={}

    def block_offset(self,block):
        if not 0<=block<self.blocks_count:
            raise FileSystemError(f'ext-Block außerhalb Dateisystem: {block}')
        return self.offset+block*self.block_size

    def _read_inode_raw(self,f,number):
        if not 1<=number<=self.inodes_count:
            raise FileSystemError('ext-Inode außerhalb des Dateisystems')
        group=(number-1)//self.inodes_per_group
        index=(number-1)%self.inodes_per_group
        if group not in self._inode_table_cache:
            d=read_exact(f,self.descriptor_offset+group*self.descriptor_size,self.descriptor_size)
            table=u32(d,8)
            if self.incompat&0x80 and len(d)>=64:
                table|=u32(d,40)<<32
            self._inode_table_cache[group]=table
        table=self._inode_table_cache[group]
        addr=self.block_offset(table)+index*self.inode_size
        return read_exact(f,addr,self.inode_size)

    def inode(self,f,number):
        raw=self._read_inode_raw(f,number)
        mode=u16(raw,0)
        flags=u32(raw,32)
        size=u32(raw,4)
        if mode&0xF000==0x8000: # regular file
            size |= u32(raw,108)<<32
        if size>MAX_FILE_SIZE:raise FileSystemError('ext-Datei unplausibel groß')
        return mode,flags,size,raw[40:100]

    def _extent_blocks(self,f,header:bytes,depth_limit=5):
        # i_block begins with extent header, then extents or index pointers.
        def walk(node,level,visited):
            if len(node)<12 or u16(node,0)!=0xF30A:
                raise FileSystemError('Ungültiger ext4-Extent-Header')
            count=u16(node,2); max_e=u16(node,4); depth=u16(node,6)
            if count>max_e or count> (len(node)-12)//12 or depth>5 or depth!=level:
                raise FileSystemError('Beschädigter ext4-Extent-Baum')
            for i in range(count):
                e=node[12+i*12:24+i*12]
                logical=u32(e,0)
                if depth==0:
                    raw_length=u16(e,4)
                    uninit=raw_length>32768
                    length=raw_length-32768 if uninit else raw_length
                    physical=(u16(e,6)<<32)|u32(e,8)
                    if length<1:raise FileSystemError('Leerer ext4-Extent')
                    yield logical,length,physical,uninit
                else:
                    child=(u16(e,8)<<32)|u32(e,4)
                    if child in visited:raise FileSystemError('Extents-Zyklus')
                    child_data=read_exact(f,self.block_offset(child),self.block_size)
                    yield from walk(child_data,depth-1,visited|{child})
        depth=u16(header,6) if len(header)>=8 else 65535
        return sorted(walk(header,depth,set()))

    def _indirect_block(self,f,block,depth,logical,needed,visited):
        if block==0:
            yield from ((logical+i,None) for i in range(needed))
            return
        if block in visited: raise FileSystemError('Zyklischer ext-Blockpointer')
        pointers=struct.unpack('<'+'I'*(self.block_size//4),read_exact(f,self.block_offset(block),self.block_size))
        span=(self.block_size//4)**(depth-1)
        for i,p in enumerate(pointers):
            start=logical+i*span
            if start>=needed:break
            if depth==1:
                yield start,(p or None)
            elif p:
                yield from self._indirect_block(f,p,depth-1,start,needed,visited|{block})
            else:
                for k in range(start,min(start+span,needed)):
                    yield k,None

    def _mapping(self,f,mode,flags,size,raw_block):
        needed=(size+self.block_size-1)//self.block_size
        if flags & 0x10000000:
            raise FileSystemError('ext4-Inline-Data nicht unterstützt')
        if flags & (0x800|0x4):
            raise FileSystemError('Verschlüsseltes/komprimiertes ext-Dateiformat nicht unterstützt')
        if flags & 0x80000:
            exts=self._extent_blocks(f,raw_block)
            used=set()
            for logical,length,physical,uninit in exts:
                if logical+length>self.blocks_count+needed:
                    raise FileSystemError('Unplausible Extent-Anzahl')
                for i in range(length):
                    key=logical+i
                    if key>=needed:break
                    if key in used:raise FileSystemError('Überlappende ext4-Extents')
                    used.add(key)
                    yield key,None if uninit else physical+i
        else:
            p=struct.unpack('<15I',raw_block)
            for i,block in enumerate(p[:12]):
                if i>=needed:break
                yield i,block or None
            at=12
            for depth,block in ((1,p[12]),(2,p[13]),(3,p[14])):
                if at>=needed:break
                span=(self.block_size//4)**depth
                yield from self._indirect_block(f,block,depth,at,min(needed,at+span),set())
                at+=span

    def _bytes_inode(self,f,number,max_bytes=None):
        mode,flags,size,raw=self.inode(f,number)
        remaining=min(size,max_bytes) if max_bytes is not None else size
        if not remaining:return
        mapping=iter(self._mapping(f,mode,flags,size,raw))
        logical=0
        while remaining:
            try:
                key,block=next(mapping)
            except StopIteration:
                key,block=(1<<62),None
            while logical<key and remaining:
                take=min(self.block_size,remaining)
                yield bytes(take)
                logical+=1;remaining-=take
            if not remaining:return
            if key<logical:raise FileSystemError('Extents nicht streng sortiert')
            take=min(self.block_size,remaining)
            if block is None:yield bytes(take)
            else:yield read_exact(f,self.block_offset(block),take)
            remaining-=take;logical+=1

    # Deleted ext2/3/4 candidates may retain inode/block pointers. We NEVER
    # infer missing pointers or use occupied blocks. An apparently free block
    # might nevertheless have been overwritten: even a successful export is
    # explicitly an unverified hypothesis, not authenticated original content.
    MAX_DELETED_EXT_BYTES = 64 * 1024 * 1024

    def _bitmap_bit(self, f, number, is_inode, bitmap_cache):
        """True when allocated, False when free, never guess on corrupt metadata."""
        if is_inode:
            if not 1 <= number <= self.inodes_count:
                raise FileSystemError('Gelöschter ext-Inode außerhalb des Volumes')
            group = (number - 1) // self.inodes_per_group
            bit = (number - 1) % self.inodes_per_group
            desc_offset = 4  # bg_inode_bitmap_lo
            high_offset = 36 # bg_inode_bitmap_hi (64-byte descriptors)
        else:
            if not self.first_data_block <= number < self.blocks_count:
                raise FileSystemError('Gelöschter ext-Datenblock außerhalb des Volumes')
            group = (number - self.first_data_block) // self.blocks_per_group
            bit = (number - self.first_data_block) % self.blocks_per_group
            desc_offset = 0  # bg_block_bitmap_lo
            high_offset = 32 # bg_block_bitmap_hi
        if group >= self.group_count or bit >= self.block_size * 8:
            raise FileSystemError('Ext-Belegungsbitmap kann Index nicht darstellen')
        key = (group, is_inode)
        if key not in bitmap_cache:
            desc = read_exact(f, self.descriptor_offset + group*self.descriptor_size,
                              self.descriptor_size)
            # ext4 flex_bg / uninitialized group bitmaps: interpreting an
            # uninitialized bitmap as "all free" would be unsafe.
            group_flags = u16(desc, 18)
            if group_flags & (0x0001 if is_inode else 0x0002):
                raise FileSystemError('Ext-Belegungsbitmap dieser Gruppe nicht initialisiert')
            bitmap_block = u32(desc, desc_offset)
            if self.incompat & 0x80:
                if len(desc) < 64:
                    raise FileSystemError('Unvollständiger ext4-64bit-Gruppendeskriptor')
                bitmap_block |= u32(desc, high_offset) << 32
            if bitmap_block <= self.first_data_block:
                raise FileSystemError('Fehlende oder unplausible ext-Belegungsbitmap')
            bitmap_cache[key] = read_exact(f, self.block_offset(bitmap_block),
                                           self.block_size)
        return bool(bitmap_cache[key][bit // 8] & (1 << (bit % 8)))

    def _deleted_blocks(self, f, number, bitmap_cache):
        """Validate ALL blocks of a small deleted regular inode, without guessing.

        First-stage recovery supports in-inode extents and legacy direct blocks.
        Indirect/extent index trees may already have been reused and are refused.
        """
        raw_inode = self._read_inode_raw(f, number)
        mode = u16(raw_inode, 0)
        links = u16(raw_inode, 26)
        deletion_time = u32(raw_inode, 20)
        flags = u32(raw_inode, 32)
        size = u32(raw_inode, 4) | (u32(raw_inode, 108) << 32)
        if (mode & 0xF000) != 0x8000 or links != 0 or deletion_time == 0:
            raise FileSystemError('Kein nachweislich gelöschter regulärer ext-Inode')
        if size > self.MAX_DELETED_EXT_BYTES:
            raise FileSystemError('Gelöschte ext-Datei für begrenzte Prüfung zu groß')
        # Bigalloc uses clusters rather than individual blocks for its bitmap.
        if self.ro_compat & 0x200:
            raise FileSystemError('ext4-Bigalloc wird bei Löschrettung nicht unterstützt')
        if flags & (0x10000000 | 0x800 | 0x4 | 0x1000):
            raise FileSystemError('Verschlüsselte, komprimierte oder Inline-ext-Datei')
        if self._bitmap_bit(f, number, True, bitmap_cache):
            raise FileSystemError('Gelöschter ext-Inode ist laut Bitmap wieder belegt')
        needed = (size + self.block_size - 1) // self.block_size
        if needed == 0:
            return size, []
        i_block = raw_inode[40:100]
        if flags & 0x80000:
            if len(i_block) < 12 or u16(i_block, 0) != 0xF30A or u16(i_block, 6) != 0:
                raise FileSystemError('Gelöschter ext4-Extent-Baum nicht vollständig im Inode')
            mapping = list(self._mapping(f, mode, flags, size, i_block))
        else:
            if needed > 12:
                raise FileSystemError('Gelöschte ext2/3-Datei benötigt ungesicherte indirekte Pointer')
            pointers = struct.unpack('<15I', i_block)
            mapping = [(i, pointers[i]) for i in range(needed)]
        if len(mapping) != needed:
            raise FileSystemError('Unvollständige alte ext-Datenblockzuordnung')
        blocks = []
        seen = set()
        for i, (logical, physical) in enumerate(mapping):
            if logical != i or physical is None or physical == 0 or physical in seen:
                raise FileSystemError('Gelöschte ext-Datei hat Löcher oder überlappende Blöcke')
            seen.add(physical)
            if self._bitmap_bit(f, physical, False, bitmap_cache):
                raise FileSystemError('Gelöschter ext-Datenblock ist bereits wieder belegt')
            blocks.append(physical)
        return size, blocks

    def assess_deleted_inode(self, f, number):
        """Return (size, limitation). Empty limitation permits *experimental* export."""
        try:
            size, blocks = self._deleted_blocks(f, number, {})
            return size, ''
        except (OSError, FileSystemError, ValueError, struct.error) as exc:
            return 0, 'ext-Löschhinweis, Export nicht möglich: ' + str(exc)

    def iter_file(self,f,entry,max_bytes=None):
        if entry.is_deleted:
            # Revalidate inode and ALL block bitmaps immediately before reading.
            size, blocks = self._deleted_blocks(f, entry.locator[0], {})
            if size != entry.size:
                raise FileSystemError('Gelöschte ext-Datei hat inzwischen andere Größe')
            remaining = min(size, max_bytes) if max_bytes is not None else size
            for block in blocks:
                if remaining <= 0:
                    break
                take = min(self.block_size, remaining)
                yield read_exact(f, self.block_offset(block), take)
                remaining -= take
            if remaining:
                raise FileSystemError('Gelöschte ext-Datei unvollständig')
            return
        yield from self._bytes_inode(f,entry.locator[0],max_bytes)

    def list_directory(self,f,locator):
        inode_no=locator[0]
        mode,flags,size,raw=self.inode(f,inode_no)
        if mode&0xF000!=0x4000:raise FileSystemError('Inode ist kein Verzeichnis')
        if size>64*1024*1024:raise FileSystemError('ext-Verzeichnis >64 MiB')
        # parse each directory block; htree indexed directories still contain leaf blocks.
        data=b''.join(self._bytes_inode(f,inode_no))
        rows=[]
        for base in range(0,len(data),self.block_size):
            block=data[base:base+self.block_size]
            pos=0
            while pos+8<=len(block):
                ino=u32(block,pos)
                reclen=u16(block,pos+4)
                namelen=block[pos+6]
                if reclen<8 or reclen%4 or pos+reclen>len(block):break
                if ino and namelen and namelen<=reclen-8:
                    name=block[pos+8:pos+8+namelen].decode('utf-8','replace')
                    if name not in ('.','..'):
                        try:
                            item_mode,item_flags,item_size,_=self.inode(f,ino)
                        except FileSystemError:
                            pos+=reclen;continue
                        directory=item_mode&0xF000==0x4000
                        regular=item_mode&0xF000==0x8000
                        unsupported='' if directory or regular else 'Linux-Spezialdatei/Symlink: kein Datenexport'
                        if item_flags& (0x10000000|0x800|0x4):
                            unsupported='Inline-, verschlüsselte oder komprimierte Datei nicht unterstützt'
                        rows.append((name,directory,item_size,(ino,),unsupported))
                # Deleted ext directory records often survive within rec_len slack.
                # Metadata-only: the old inode/data extents may have been reused.
                actual_min = (8 + namelen + 3) & ~3
                candidate_at = pos + max(8,actual_min)
                while candidate_at + 8 <= pos+reclen:
                    possible = u32(block,candidate_at)
                    possible_len = u16(block,candidate_at+4)
                    possible_namelen = block[candidate_at+6]
                    remaining_slot = pos+reclen-candidate_at
                    if (possible and possible <= self.inodes_count and
                        possible_len >= 8 and possible_len%4 == 0 and
                        possible_len <= remaining_slot and
                        1 <= possible_namelen <= min(255,possible_len-8)):
                        raw_name = bytes(block[candidate_at+8:candidate_at+8+possible_namelen])
                        try:
                            old_name=raw_name.decode('utf-8','strict')
                            inode_raw=self._read_inode_raw(f,possible)
                            links=u16(inode_raw,26)
                            dtime=u32(inode_raw,20)
                            mode_old=u16(inode_raw,0)
                            if (old_name not in ('.','..') and
                                all(ord(c) >= 32 and c not in '/\\' for c in old_name) and
                                links == 0 and dtime != 0 and (mode_old & 0xF000) in (0x8000,0x4000)):
                                old_dir=(mode_old & 0xF000)==0x4000
                                old_size = self.inode(f, possible)[2]
                                reason = 'Gelöschter ext-Ordner: Datenzuordnung ungesichert'
                                if not old_dir:
                                    checked_size, reason = self.assess_deleted_inode(f, possible)
                                    if not reason:
                                        old_size = checked_size
                                rows.append((old_name, old_dir, old_size, (possible,), reason, True))
                        except (UnicodeDecodeError,OSError,ValueError,struct.error,FileSystemError):
                            pass
                        candidate_at += possible_len
                    else:
                        candidate_at += 4
                pos+=reclen
        return rows


def detect_volume(f, offset):
    b=read_exact(f,offset,512)
    if b[3:11]==b'EXFAT   ':return ExFAT(f,offset)
    if b[82:90]==b'FAT32   ':return FAT32(f,offset)
    if read_exact(f,offset+1024+56,2)==b'\x53\xef':return Ext(f,offset)
    if b[:4]==b'XFSB':
        from .linux_advanced import XFS
        return XFS(f,offset)
    if read_exact(f,offset+65536+0x40,8)==b'_BHRfS_M':
        from .linux_advanced import Btrfs
        return Btrfs(f,offset)
    raise FileSystemError('Kein unterstütztes NTFS-, FAT32-, exFAT-, ext-, Btrfs- oder XFS-Dateisystem gefunden')


def scan_tree(path: str, offset: int = 0, max_entries: int = MAX_ENTRIES,
              progress: Callable[[int,int],None] | None = None,
              cancel: Callable[[],bool] | None = None,
              tolerate_read_errors: bool = False) -> GenericIndex:
    """Index reachable entries from FAT32, exFAT, ext and advanced Linux FS.

    Optional image-only tolerant mode skips individual unreadable subfolders.
    No attempt is made to repair directory blocks or fabricate filenames.
    """
    if offset < 0 or offset % 512:
        raise ValueError('Partitionsoffset muss 512-Byte-ausgerichtet sein')
    if max_entries < 1 or max_entries > MAX_ENTRIES:
        raise ValueError('Ungültiges Eintragslimit')
    if tolerate_read_errors and is_device_source(path):
        raise FileSystemError('Fehlertolerante Suche nur für Images; '
                              'bei beschädigter Hardware zuerst ein Abbild erstellen.')
    entries = []
    children = defaultdict(list)
    failures = []
    unreadable_dirs = 0
    with open_source(path) as f:
        volume = detect_volume(f, offset)
        if isinstance(volume, FAT32):
            root = (volume.root_cluster,)
        elif isinstance(volume, ExFAT):
            root = (volume.root_cluster, False, None)
        elif hasattr(volume, 'root_locator'):
            root = volume.root_locator
        else:
            root = (2,)
        todo = deque([(ROOT, root, 0)])
        visited = {root[0]}
        serial = 6
        by_id = {}
        while todo:
            if cancel and cancel():
                raise ScanCancelled('Scan durch Benutzer abgebrochen')
            parent, locator, depth = todo.popleft()
            if depth > 128:
                raise FileSystemError('Verzeichnisverschachtelung >128 Ebenen')
            try:
                rows = volume.list_directory(f, locator)
            except (OSError, FileSystemError, ValueError, struct.error) as exc:
                if not tolerate_read_errors or parent == ROOT:
                    raise
                unreadable_dirs += 1
                if parent in by_id:
                    by_id[parent].unsupported_reason = 'Inhalt dieses Ordners nicht lesbar'
                if len(failures) < 100:
                    failures.append(f'Ordner-ID {parent}, Dateisystem-Locator {locator[0]}: {exc}')
                if progress:
                    progress(len(entries), max_entries)
                continue
            for row in rows:
                if len(row) == 6:
                    name, directory, size, loc, reason, deleted = row
                else:
                    name, directory, size, loc, reason = row
                    deleted = False
                if len(entries) >= max_entries:
                    raise FileSystemError(f'Eintragslimit von {max_entries:,} erreicht; '
                                          'nur Teilansicht. Limit im Code erhöhen')
                serial += 1
                entry = GenericEntry(serial, name, parent, directory, size, loc,
                                     is_deleted=deleted, unsupported_reason=reason)
                entries.append(entry)
                by_id[entry.record_number] = entry
                children[parent].append(entry)
                if directory and not deleted and not reason and loc[0] not in visited:
                    visited.add(loc[0])
                    todo.append((entry.record_number, loc, depth+1))
            if progress:
                progress(len(entries), max_entries)
        # Conservative filesystem-specific metadata hints. Query ONLY image
        # files: avoid additional probes on potentially failing physical disks.
        # These synthetic entries are NOT full deleted file reconstructions.
        if not is_device_source(path) and hasattr(volume, 'deletion_hints'):
            try:
                hints = volume.deletion_hints(f, limit=min(256, max_entries-len(entries)))
                for name, directory, size, loc, reason, deleted in hints:
                    serial += 1
                    item = GenericEntry(serial, name, ROOT, directory, size, loc,
                                        is_deleted=True, unsupported_reason=reason)
                    entries.append(item)
                    by_id[item.record_number] = item
                    children[ROOT].append(item)
                if hints:
                    failures.append(f'{len(hints)} Btrfs/XFS-Orphan-Hinweise: '
                                    'nur Metadaten; nicht exportierbar')
            except (FileSystemError, OSError, ValueError, struct.error) as exc:
                failures.append(f'Orphan-Metadatensuche übersprungen: {exc}')
    return GenericIndex(volume.label, offset, entries, volume, dict(children),
                        len(entries), len(entries), unreadable_directories=unreadable_dirs,
                        scan_warnings=failures, tolerant=tolerate_read_errors)


def export_file(source, index: GenericIndex, entry: GenericEntry, dest: str,
                cancel=None, byte_progress=None) -> int:
    if not entry.recoverable:
        raise FileSystemError(entry.unsupported_reason or 'Kein Datei-Eintrag')
    ensure_safe_destination(source, dest)
    if os.path.lexists(dest):
        raise FileExistsError(dest)
    created = False
    with open_source(source) as f:
        try:
            with open(dest, 'xb', buffering=0) as out:
                created = True
                written = write_chunks(out, index.volumes.iter_file(f, entry),
                                       cancel=cancel, byte_progress=byte_progress)
                if written != entry.size:
                    raise FileSystemError(f'Unvollständige Datei ({written} von {entry.size} Bytes)')
                out.flush()
                os.fsync(out.fileno())
        except Exception:
            if created:
                try: os.unlink(dest)
                except OSError: pass
            raise
    return written


def export_selection(source,index:GenericIndex,selection,target_dir,progress=None,cancel=None,
                     byte_progress=None)->ExportReport:
    if not os.path.isdir(target_dir):raise ValueError('Zielordner existiert nicht')
    ensure_safe_destination(source,target_dir)
    report=ExportReport()
    stack=[(e,target_dir,frozenset()) for e in reversed(list(selection))]
    while stack:
        if cancel and cancel():
            report.errors.append('Export abgebrochen');report.cancelled=True;break
        entry,directory,ancestry=stack.pop()
        if entry.record_number in ancestry:
            report.skipped+=1;continue
        try:
            name=safe_name(entry.name,entry.record_number)
            target=os.path.join(directory,name)
            if os.path.lexists(target):
                stem,ext=os.path.splitext(name)
                target=os.path.join(directory,f'{stem}__ID{entry.record_number}{ext}')
            if os.path.lexists(target):
                raise FileExistsError(target)
            ensure_safe_destination(source,target)
            if entry.is_directory:
                os.mkdir(target)
                report.directories+=1
                stack.extend((e,target,ancestry|{entry.record_number}) for e in reversed(index.list_dir(entry.record_number)))
            elif entry.recoverable:
                count = export_file(source,index,entry,target,cancel=cancel,byte_progress=byte_progress)
                report.bytes_written += count
                report.exported+=1
                if progress:progress(entry.name)
            else:
                report.skipped+=1
                report.errors.append(f'{entry.name}: {entry.unsupported_reason}')
        except ExportCancelled:
            report.cancelled=True
            report.errors.append('Export während der Datei abgebrochen; unvollständige Zieldatei entfernt.')
            break
        except (OSError,ValueError,FileSystemError) as ex:
            report.skipped+=1;report.errors.append(f'{entry.name}: {ex}')
    return report
