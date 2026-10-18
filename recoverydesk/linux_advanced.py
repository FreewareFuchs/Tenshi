"""Conservative, read-only Btrfs (single device) and XFS directory readers.

Purpose: recover *allocated* directory entries and ordinary uncompressed files.
No journal/log replay, no snapshot reconstruction, no RAID reconstruction,
no checksum repair, no write path. Unsupported formats FAIL CLOSED.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import struct
from typing import Iterator

from .filesystems import VolumeBase, FileSystemError, MAX_FILE_SIZE, read_exact


def le16(b, p=0): return struct.unpack_from('<H', b, p)[0]
def le32(b, p=0): return struct.unpack_from('<I', b, p)[0]
def le64(b, p=0): return struct.unpack_from('<Q', b, p)[0]
def be16(b, p=0): return struct.unpack_from('>H', b, p)[0]
def be32(b, p=0): return struct.unpack_from('>I', b, p)[0]
def be64(b, p=0): return struct.unpack_from('>Q', b, p)[0]


@dataclass(frozen=True)
class BtrfsChunk:
    logical: int
    length: int
    physical: int


class Btrfs(VolumeBase):
    """Browse default filesystem tree of an uncompressed, single-device Btrfs volume.

    Supports regular/inline file extents and sparse holes, without decompressing.
    Rejects RAID, multi-device, unsupported extents, and unsupported subvolumes
    rather than silently exporting wrong bytes.
    """
    label = 'Btrfs'
    root_locator = ((5<<64)|256,)

    def __init__(self, f, offset):
        super().__init__(offset)
        sb = read_exact(f, offset + 65536, 4096)
        if sb[0x40:0x48] != b'_BHRfS_M':
            raise FileSystemError('Kein Btrfs-Superblock bei +64 KiB')
        self.total_bytes = le64(sb, 0x70)
        self.num_devices = le64(sb, 0x88)
        self.sectorsize = le32(sb, 0x90)
        self.nodesize = le32(sb, 0x94)
        self.root_bytenr = le64(sb, 0x50)
        self.chunk_root = le64(sb, 0x58)
        self.chunk_array_size = le32(sb, 0xA0)
        if self.num_devices != 1:
            raise FileSystemError('Btrfs mit mehreren Geräten: Einzel-RAW-Image ist nicht ausreichend.')
        if self.sectorsize not in (4096, 8192, 16384, 32768, 65536) or self.nodesize not in (4096,8192,16384,32768,65536):
            raise FileSystemError('Btrfs-Sektor-/Knotengröße nicht unterstützt')
        if not (0 < self.total_bytes <= MAX_FILE_SIZE * 256) or not (0 < self.chunk_array_size <= 2048):
            raise FileSystemError('Unplausibler Btrfs-Superblock')
        self.chunks = []
        self._dirs = defaultdict(list)
        self._sizes = {}
        self._types = {}
        self._extents = defaultdict(list)
        self._tree_cache = {}
        self._orphan_hints = []  # (tree_id, inode): Btrfs orphan metadata, not a recoverable file
        self._parse_chunks(sb[0x32b:0x32b+self.chunk_array_size], single_entry=False)
        if not self.chunks:
            raise FileSystemError('Btrfs-System-Chunkmapping fehlt')
        # Chunk tree itself must be reachable via bootstrap system chunks.
        for (objectid, kind, key_offset), raw in self._tree_items(f, self.chunk_root):
            if kind == 228:  # CHUNK_ITEM
                self._parse_chunks(struct.pack('<QBQ', objectid, kind, key_offset) + raw, single_entry=True)
        # Root tree locates FS tree 5 plus referenced subvolumes/snapshots.
        # Each object ID is made unique across trees by combining tree/inode.
        fs_roots = {}
        for (objectid, kind, key_offset), raw in self._tree_items(f, self.root_bytenr):
            if kind == 132 and len(raw) >= 184 and (objectid == 5 or 256 <= objectid < (1<<63)):
                fs_roots[objectid] = le64(raw, 176)
        if not fs_roots.get(5):
            raise FileSystemError('Btrfs: Standard-Dateisystembaum (Root 5) nicht gefunden')
        pending = [5]
        seen_roots = set()
        while pending:
            tree_id = pending.pop()
            if tree_id in seen_roots: continue
            seen_roots.add(tree_id)
            if len(seen_roots) > 128:
                raise FileSystemError('Btrfs: zu viele Untervolumes (Limit 128)')
            tree_bytenr = fs_roots.get(tree_id)
            if not tree_bytenr: continue
            for (objectid, kind, key_offset), raw in self._tree_items(f, tree_bytenr):
                composite = (tree_id<<64) | objectid
                if kind == 1 and len(raw) >= 56:  # INODE_ITEM
                    self._sizes[composite] = le64(raw, 16)
                    self._types[composite] = le32(raw, 52) & 0xF000
                elif kind == 96 and len(raw) >= 30:  # DIR_INDEX
                    entry_obj = le64(raw, 0)
                    entry_type = raw[8]
                    data_len = le16(raw, 25)
                    name_len = le16(raw, 27)
                    file_type = raw[29]
                    if 0 < name_len <= 255 and 30 + name_len + data_len <= len(raw):
                        name = raw[30:30+name_len].decode('utf-8', 'replace')
                        if name in ('.', '..'): continue
                        reason = ''
                        if entry_type == 132:
                            target = (entry_obj<<64)|256
                            if entry_obj in fs_roots:
                                pending.append(entry_obj)
                            else:
                                reason = 'Btrfs-Untervolume ohne lesbaren Root-Item'
                        else:
                            target = (tree_id<<64)|entry_obj
                            if file_type not in (1,2):
                                reason = 'Btrfs-Spezialdatei oder symbolischer Link'
                        self._dirs[composite].append((name, file_type == 2 or entry_type == 132,
                                                     target, reason))
                elif kind == 108:  # EXTENT_DATA
                    self._extents[composite].append((key_offset, raw))
                elif kind == 48 and objectid == (1 << 64) - 5:  # BTRFS_ORPHAN_ITEM_KEY
                    # These mark unlinked/truncated inodes still tracked by the
                    # filesystem. They do NOT establish deleted file contents.
                    if 256 <= key_offset < (1 << 63) and len(self._orphan_hints) < 1024:
                        self._orphan_hints.append((tree_id, key_offset))

    def deletion_hints(self, f, limit=256):
        """Return metadata-only orphan hints; never claim exportability."""
        if limit <= 0:
            return []
        referenced = {target for children in self._dirs.values()
                      for _, _, target, _ in children}
        rows = []
        for tree_id, ino in dict.fromkeys(self._orphan_hints):
            composite = (tree_id << 64) | ino
            if composite in referenced:
                continue  # A live directory entry takes precedence.
            size = self._sizes.get(composite, 0)
            reason = ('Btrfs-Orphan-Metadaten (unverknüpft/Trunkierung); '
                      'Dateiname und Datenintegrität nicht überprüfbar; kein Export')
            rows.append((f'Btrfs-Orphan-Inode {ino} (Subvolume {tree_id})',
                         False, size, (composite,), reason, True))
            if len(rows) >= limit:
                break
        return rows

    def _parse_chunks(self, blob, single_entry=False):
        p = 0
        while p + 17 + 48 + 32 <= len(blob):
            objectid, kind, logical = struct.unpack_from('<QBQ', blob, p)
            p += 17
            if kind != 228:
                if single_entry:
                    raise FileSystemError('Unerwarteter Btrfs-Chunk-Schlüssel')
                raise FileSystemError('Ungültiger Btrfs-System-Chunk-Schlüssel')
            length = le64(blob, p)
            profile = le64(blob, p+24)
            stripe_count = le16(blob, p+44)
            if stripe_count < 1 or stripe_count > 64 or p+48+stripe_count*32 > len(blob):
                raise FileSystemError('Fehlerhafter Btrfs-Chunk-Eintrag')
            # Btrfs feature bitmask: only SINGLE and one-stripe DUP-free
            # mappings are accepted; RAID0/1/10/5/6/1c3/... require more context.
            # DUP stores 2 copies on the SAME device; the first can be
            # read without RAID reconstruction. Do not accept RAID1/0/10/5 etc.
            dup = bool(profile & 0x20)
            if (profile & ~(0x7|0x20)) or stripe_count != (2 if dup else 1):
                raise FileSystemError('Btrfs-RAID/Mehrfachstreifen kann nicht sicher gelesen werden.')
            device_id = le64(blob, p+48)
            physical = le64(blob, p+56)
            if dup and device_id != le64(blob, p+80):
                raise FileSystemError('Btrfs-DUP-Streifen liegen auf verschiedenen Geräten')
            if length and device_id > 0:
                self.chunks.append(BtrfsChunk(logical, length, physical))
            p += 48 + stripe_count*32
            if single_entry:
                break

    def _physical(self, logical, length):
        for chunk in reversed(self.chunks):
            if chunk.logical <= logical and logical + length <= chunk.logical + chunk.length:
                return self.offset + chunk.physical + logical - chunk.logical
        raise FileSystemError(f'Btrfs: kein physisches Mapping für logische Adresse {logical}')

    def _logical_data(self, f, logical, length):
        # Multi-chunk range resolution; also works with aligned raw device wrapper.
        pos, remaining = logical, length
        while remaining:
            chunk = next((c for c in reversed(self.chunks) if c.logical <= pos < c.logical+c.length), None)
            if chunk is None:
                raise FileSystemError(f'Btrfs: Chunk für {pos} fehlt')
            amount = min(remaining, chunk.logical + chunk.length - pos, 1024*1024)
            yield read_exact(f, self.offset + chunk.physical + pos - chunk.logical, amount)
            pos += amount
            remaining -= amount

    def _tree_items(self, f, root):
        """Bounded tree walk, with loop/owner guards, returns (key, data)."""
        todo = [root]
        visited = set()
        while todo:
            logical = todo.pop()
            if logical in visited:
                raise FileSystemError('Zyklischer oder gemeinsam referenzierter Btrfs-Baumblock')
            visited.add(logical)
            if len(visited) > 200_000:
                raise FileSystemError('Btrfs-Scanlimit (200.000 Knoten) erreicht')
            block = read_exact(f, self._physical(logical, self.nodesize), self.nodesize)
            if le64(block, 48) != logical:
                raise FileSystemError('Btrfs: Baumblock-Adresse stimmt nicht überein')
            count = le32(block, 96)
            level = block[100]
            if level > 8 or count > (self.nodesize-101)//(33 if level else 25):
                raise FileSystemError('Btrfs: beschädigter Baumblock-Header')
            if level:
                pointers = []
                for i in range(count):
                    p = 101+i*33
                    pointers.append(le64(block, p+17))
                todo.extend(reversed(pointers))
            else:
                for i in range(count):
                    p = 101+i*25
                    key = (le64(block,p), block[p+8], le64(block,p+9))
                    item_start, item_length = le32(block,p+17), le32(block,p+21)
                    if 101 + item_start + item_length > self.nodesize:
                        raise FileSystemError('Btrfs: defekter Blattdatensatz')
                    yield key, block[101+item_start:101+item_start+item_length]

    def list_directory(self, f, locator):
        ino = locator[0]
        rows = []
        for name, is_dir, target, reason in self._dirs.get(ino, ()):
            size = self._sizes.get(target, 0)
            if not is_dir and target not in self._sizes:
                reason = reason or 'Btrfs-Inode-Metadaten fehlen'
            rows.append((name, is_dir, 0 if is_dir else size, (target,), reason))
        return rows

    def iter_file(self, f, entry, max_bytes=None) -> Iterator[bytes]:
        if entry.unsupported_reason:
            raise FileSystemError(entry.unsupported_reason)
        size = entry.size
        if size > MAX_FILE_SIZE:
            raise FileSystemError('Btrfs-Datei zu groß')
        remaining = min(size, max_bytes) if max_bytes is not None else size
        current = 0
        for file_offset, raw in sorted(self._extents.get(entry.locator[0], [])):
            if remaining <= 0: break
            if file_offset > current:
                hole = min(remaining, file_offset-current)
                for p in range(0, hole, 1024*1024):
                    yield bytes(min(1024*1024, hole-p))
                current += hole; remaining -= hole
            if file_offset < current:
                raise FileSystemError('Btrfs überlappende Dateiextents')
            if len(raw) < 21:
                raise FileSystemError('Btrfs Extent verkürzt')
            comp, encryption, encoding, kind = raw[16], raw[17], le16(raw,18), raw[20]
            if comp or encryption or encoding:
                raise FileSystemError('Btrfs komprimierte/verschlüsselte Datei nicht unterstützt')
            if kind == 0:
                data = raw[21:]
                amount = min(remaining, len(data))
                if amount: yield data[:amount]
            elif kind in (1, 2):
                if len(raw) < 53:
                    raise FileSystemError('Btrfs reguläres Extent verkürzt')
                disk_bytenr, disk_length, extent_offset, num_bytes = struct.unpack_from('<QQQQ', raw, 21)
                amount = min(remaining, num_bytes)
                if disk_bytenr == 0 or kind == 2:
                    # Preallocated extents and explicit holes read as zeroes.
                    for _ in range(0, amount, 1024*1024):
                        yield bytes(min(1024*1024, amount-_))
                else:
                    yield from self._logical_data(f, disk_bytenr + extent_offset, amount)
            else:
                raise FileSystemError('Btrfs Extent-Typ nicht unterstützt')
            remaining -= amount
            current += amount
        if remaining:
            for p in range(0, remaining, 1024*1024):
                yield bytes(min(1024*1024, remaining-p))


@dataclass(frozen=True)
class XfsInode:
    number: int
    mode: int
    size: int
    format: int
    data: bytes
    nextents: int
    flags: int


class XFS(VolumeBase):
    """XFS v4/v5 basic shortform and extent-based directories, allocated files."""
    label = 'XFS'

    def __init__(self, f, offset):
        super().__init__(offset)
        sb = read_exact(f, offset, 512)
        if sb[:4] != b'XFSB':
            raise FileSystemError('Kein XFS-Superblock')
        self.blocksize = be32(sb,4)
        self.dblocks = be64(sb,8)
        self.root_ino = be64(sb,56)
        self.agblocks = be32(sb,84)
        self.agcount = be32(sb,88)
        self.inodesize = be16(sb,104)
        self.sectorsize = be16(sb,102)
        self.blocklog = sb[120]
        self.inodelog = sb[122]
        self.inopblog = sb[123]
        self.agblklog = sb[124]
        self.version = be16(sb,100) & 0xf
        self.features2 = be32(sb,200) if len(sb)>=204 else 0  # conservative fallback
        self.root_locator = (self.root_ino,)
        if (self.blocksize not in (512,1024,2048,4096,8192,16384,32768,65536)
            or self.inodesize not in (256,512,1024,2048) or self.sectorsize not in (512,1024,2048,4096)
            or 1<<self.blocklog != self.blocksize or 1<<self.inodelog != self.inodesize
            or (1<<self.inopblog)*self.inodesize != self.blocksize
            or not (1 <= self.agblocks <= self.dblocks and 1 <= self.agcount <= 1000000)
            or not 1 <= self.agblklog <= 40 or self.version not in (4,5)):
            raise FileSystemError('Unplausible XFS-Superblockwerte')
        if not self.root_ino:
            raise FileSystemError('XFS Root-Inode fehlt')

    def deletion_hints(self, f, limit=256):
        """Inspect the 64 AGI unlinked-list HEADS per AG, read-only.

        A head denotes an inode that has been unlinked while open. It does
        not prove that the inode's old file data still exists. We do not
        traverse on-disk next_unlinked pointers or reconstruct file names.
        """
        if limit <= 0:
            return []
        rows = []
        seen = set()
        max_ag = min(self.agcount, 256)  # bounded forensic metadata probe
        for agno in range(max_ag):
            # AGI is at two logical sectors from the AG start.
            agi_offset = self.offset + agno * self.agblocks * self.blocksize + 2 * self.sectorsize
            try:
                data = read_exact(f, agi_offset, max(self.sectorsize, 512))
            except (OSError, FileSystemError):
                continue  # a broken AGI must not prevent normal file browsing
            if (data[:4] != b'XAGI' or be32(data, 4) != 1 or
                be32(data, 8) != agno or not (1 <= be32(data, 12) <= self.agblocks)):
                continue
            # Header's first ten 32-bit fields = 40 bytes; then 64 heads.
            for bucket in range(64):
                relative_ino = be32(data, 40 + 4 * bucket)
                if relative_ino == 0xffffffff or relative_ino >= self.agblocks * (1 << self.inopblog):
                    continue
                ino = (agno << (self.agblklog + self.inopblog)) | relative_ino
                if ino in seen or ino == self.root_ino:
                    continue
                seen.add(ino)
                try:
                    item = self._inode(f, ino)
                    # Core XFS dinode field di_nlink at offset 16. Nonzero
                    # nlink means not a validated unlink hint.
                    agblk = (ino >> self.inopblog) & ((1 << self.agblklog) - 1)
                    index = ino & ((1 << self.inopblog) - 1)
                    inode_pos = self._absolute_block(agno * self.agblocks + agblk) + index * self.inodesize
                    header = read_exact(f, inode_pos, 20)
                    if be32(header, 16) != 0 or item.mode & 0xF000 not in (0x8000, 0x4000):
                        continue
                except (OSError, FileSystemError, ValueError, struct.error):
                    continue
                rows.append((f'XFS-Unlinked-Inode {ino} (AG {agno})', False,
                            item.size, (ino,),
                            'XFS-AGI-Unlinked-Metadaten; Dateiname/Datenbelegung ungeprüft; kein Export', True))
                if len(rows) >= limit:
                    return rows
        return rows

    def _absolute_block(self, absolute_block):
        if absolute_block >= self.dblocks:
            raise FileSystemError('XFS Block außerhalb des Volumes')
        return self.offset + absolute_block*self.blocksize

    def _fs_block(self, encoded_block):
        # xfs_fsblock_t uses AG-number in the high bits and AG-relative
        # block number in the low agblklog bits (AG lengths need not be 2^n).
        agno = encoded_block >> self.agblklog
        agbno = encoded_block & ((1<<self.agblklog)-1)
        if agno >= self.agcount or agbno >= self.agblocks:
            raise FileSystemError('XFS Extent verweist auf ungültige Allocation Group')
        return self._absolute_block(agno*self.agblocks+agbno)

    def _inode(self, f, ino):
        # XFS inode number: AG number / AG block number / inode-offset within block.
        agno = ino >> (self.agblklog+self.inopblog)
        agbno = (ino >> self.inopblog) & ((1<<self.agblklog)-1)
        index = ino & ((1<<self.inopblog)-1)
        if agno >= self.agcount or agbno >= self.agblocks:
            raise FileSystemError('XFS Inode außerhalb der Allocation Group')
        position = self._absolute_block(agno*self.agblocks+agbno) + index*self.inodesize
        raw = read_exact(f, position, self.inodesize)
        if raw[:2] != b'IN' or raw[4] not in (2,3):
            raise FileSystemError(f'XFS Inode {ino} ist beschädigt oder nicht belegt')
        mode, fmt = be16(raw,2), raw[5]
        size, nextents = be64(raw,56), be32(raw,76)
        forkoff = raw[82]
        data_start = 176 if raw[4] == 3 else 100
        data_end = min(self.inodesize, forkoff*8 if forkoff else self.inodesize)
        if data_end < data_start or fmt not in (1,2,3) or size > MAX_FILE_SIZE:
            raise FileSystemError('XFS ungültiges Inode-Format/Dateigröße')
        return XfsInode(ino, mode, size, fmt, raw[data_start:data_end], nextents, be16(raw,90))

    def _extents(self, inode):
        if inode.format != 2:
            raise FileSystemError('XFS Btree-Extent-Format derzeit nicht unterstützt')
        if inode.nextents > len(inode.data)//16:
            raise FileSystemError('XFS Extent-Liste abgeschnitten')
        result = []
        for i in range(inode.nextents):
            word = int.from_bytes(inode.data[i*16:(i+1)*16], 'big')
            unwritten = bool(word>>127)
            logical = (word>>73)&((1<<54)-1)
            block = (word>>21)&((1<<52)-1)
            count = word&((1<<21)-1)
            agno = block >> self.agblklog
            agbno = block & ((1<<self.agblklog)-1)
            if count <= 0 or agno >= self.agcount or agbno + count > self.agblocks or agno*self.agblocks + agbno + count > self.dblocks:
                raise FileSystemError('XFS Extent zeigt über den Datenträger hinaus')
            result.append((logical, block, count, unwritten))
        result.sort()
        return result

    def _bytes(self, f, inode, limit=None):
        remaining = min(inode.size, limit) if limit is not None else inode.size
        if not remaining: return
        if inode.format == 1:
            if remaining > len(inode.data):
                raise FileSystemError('XFS lokale Daten abgeschnitten')
            yield inode.data[:remaining]
            return
        current = 0
        for logical, block, count, unwritten in self._extents(inode):
            if remaining <= 0:break
            start = logical*self.blocksize
            if start < current:
                raise FileSystemError('XFS überlappende Extents')
            hole = min(start-current, remaining)
            for pos in range(0,hole,1024*1024):
                yield bytes(min(1024*1024,hole-pos))
            remaining -= hole; current += hole
            amount = min(remaining, count*self.blocksize)
            if unwritten:
                for pos in range(0,amount,1024*1024):
                    yield bytes(min(1024*1024,amount-pos))
            else:
                for pos in range(0,amount,1024*1024):
                    yield read_exact(f,self._fs_block(block)+pos,min(1024*1024,amount-pos))
            remaining -= amount;current += amount
        if remaining:
            for pos in range(0,remaining,1024*1024):
                yield bytes(min(1024*1024,remaining-pos))

    def iter_file(self, f, entry, max_bytes=None):
        inode = self._inode(f,entry.locator[0])
        if inode.mode&0xF000!=0x8000:
            raise FileSystemError('XFS keine reguläre Datei')
        yield from self._bytes(f,inode,max_bytes)

    def list_directory(self, f, locator):
        inode = self._inode(f,locator[0])
        if inode.mode & 0xF000 != 0x4000:
            raise FileSystemError('XFS Inode ist kein Verzeichnis')
        if inode.size > 64*1024*1024:
            raise FileSystemError('XFS Verzeichnis >64 MiB')
        if inode.format == 1:
            raw = inode.data[:inode.size]
            if len(raw) < 6: raise FileSystemError('XFS Shortform-Verzeichnis verkürzt')
            count, i8count = raw[0], raw[1]
            wide = i8count != 0
            pos = 2+(8 if wide else 4)
            names = []
            for _ in range(count):
                if pos+3>len(raw):raise FileSystemError('XFS Verzeichniseintrag abgeschnitten')
                n = raw[pos]
                pos += 3  # namelen + offset(2)
                if n == 0 or pos+n+(8 if wide else 4)>len(raw):
                    raise FileSystemError('XFS Shortform-Name ungültig')
                name = raw[pos:pos+n].decode('utf-8','replace');pos += n
                # v5 and v4 with ftype feature store a type byte before inode.
                has_ftype = self.version == 5 or bool(self.features2 & 0x200)
                if has_ftype:
                    if pos>=len(raw):raise FileSystemError('XFS Filetype-Feld fehlt')
                    pos += 1
                if pos+(8 if wide else 4)>len(raw):
                    raise FileSystemError('XFS Inode-Referenz fehlt')
                target = (be64(raw,pos) if wide else be32(raw,pos));pos += 8 if wide else 4
                if name not in ('.','..'):
                    names.append((name,target))
        elif inode.format == 2:
            raw = b''.join(self._bytes(f,inode))
            names = []
            for i in range(0,len(raw),self.blocksize):
                b = raw[i:i+self.blocksize]
                if len(b)<64 or b[:4] not in (b'XDB3',b'XDD3',b'XD2B',b'XD2D'):
                    continue
                v3 = b[:4] in (b'XDB3',b'XDD3')
                pos = 64 if v3 else 16
                limit = len(b)
                if b[:4] in (b'XDB3',b'XD2B'):
                    # blockdir footer stores leaf record count before final eight bytes.
                    count = be32(b,len(b)-8)
                    if count < self.blocksize//8:
                        limit = max(pos,len(b)-8-count*8)
                while pos+12<=limit:
                    if be16(b,pos) == 0xFFFF:
                        free = be16(b,pos+2)
                        if free < 6 or pos+free>limit:break
                        pos += free
                        continue
                    n = b[pos+8]
                    step = ((8+1+n+(1 if v3 or self.version==5 else 0)+2+7)//8)*8
                    if not 1<=n<=255 or pos+step>limit:break
                    name = b[pos+9:pos+9+n].decode('utf-8','replace')
                    target = be64(b,pos)
                    if name not in ('.','..'):
                        names.append((name,target))
                    pos += step
        else:
            raise FileSystemError('XFS Btree-Verzeichnisformat noch nicht unterstützt')
        rows=[]
        for name,target in names:
            try:
                child=self._inode(f,target)
            except FileSystemError:
                rows.append((name,False,0,(target,), 'XFS-Inode beschädigt oder nicht lesbar'))
                continue
            kind = child.mode&0xF000
            directory = kind==0x4000
            regular = kind==0x8000
            reason = '' if directory or (regular and child.format in (1,2)) else 'XFS Spezialdatei/Btree-Format nicht unterstützt'
            if regular and child.format==3:
                reason='XFS große Datei mit Btree-Extents nicht unterstützt'
            rows.append((name,directory,child.size,(target,),reason))
        return rows
