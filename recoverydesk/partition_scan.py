"""Read-only partition-table and filesystem candidate discovery in flat RAW images.

Only parses metadata or searches for filesystem signatures. Never repairs/writes images.
Physical sector size of the *image layout* can be 512 or 4096 bytes. Detection is
heuristic when no valid partition table is present; candidates require confirmation.
"""
from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass, field
from typing import Callable
from .sources import source_size, open_source

SECTOR_SIZES = (512, 4096)
EXTENDED_TYPES = {0x05, 0x0F, 0x85}


@dataclass
class Partition:
    index: int
    scheme: str
    start_lba: int
    sectors: int
    type_code: str
    name: str = ""
    sector_size: int = 512
    filesystem: str = "unbekannt"
    warning: str = ""
    confidence: str = "Ungeprüft"
    evidence: list[str] = field(default_factory=list)

    @property
    def offset_bytes(self) -> int:
        return self.start_lba * self.sector_size

    @property
    def size_bytes(self) -> int:
        return self.sectors * self.sector_size

    @property
    def end_lba(self) -> int:
        return self.start_lba + self.sectors - 1


@dataclass
class AnalysisReport:
    image_size: int
    partitions: list[Partition] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scanned_bytes: int = 0
    table_type: str = "keine"
    sector_size: int = 512

    @property
    def candidates(self) -> int:
        return sum(p.scheme.startswith("Fund") or p.scheme == "Volume" for p in self.partitions)


def _read_at(f, offset: int, length: int) -> bytes:
    if offset < 0 or length < 0:
        return b""
    f.seek(offset)
    return f.read(length)


def _valid_sector_size(value: int | str) -> tuple[int, ...]:
    if value == "auto":
        return SECTOR_SIZES
    try:
        size = int(value)
    except (TypeError, ValueError) as e:
        raise ValueError("Sektorgröße muss 'auto', 512 oder 4096 sein.") from e
    if size not in SECTOR_SIZES:
        raise ValueError("Sektorgröße muss 512 oder 4096 sein.")
    return (size,)


def _mbr_entries(data: bytes):
    if len(data) < 512 or data[510:512] != b"\x55\xaa":
        return []
    result = []
    for i in range(4):
        o = 446 + 16 * i
        status, typ, start, count = data[o], data[o+4], struct.unpack_from("<I", data, o+8)[0], struct.unpack_from("<I", data, o+12)[0]
        if typ and count and status in (0, 0x80):
            result.append((i+1, typ, start, count))
    return result


def _read_mbr(f, size: int, ss: int, report: AnalysisReport) -> tuple[list[Partition], bool]:
    entries = _mbr_entries(_read_at(f, 0, 512))
    if not entries:
        return [], False
    parts: list[Partition] = []
    has_protective = False
    logical_index = 5
    for number, typ, start, count in entries:
        if typ == 0xEE:
            has_protective = True
            continue
        if typ in EXTENDED_TYPES:
            # EBR chain: first entry is relative to current EBR, second to base EBR.
            base = start
            current = base
            visited = set()
            for _ in range(256):
                if current in visited or current * ss + 512 > size:
                    break
                visited.add(current)
                chain = _mbr_entries(_read_at(f, current * ss, 512))
                data_entries = [(t, rel, n) for _, t, rel, n in chain if t not in EXTENDED_TYPES and t != 0xEE]
                if data_entries:
                    t, rel, n = data_entries[0]
                    lba = current + rel
                    if lba and lba * ss < size:
                        warning = "" if (lba + n) * ss <= size else "Partition größer als Image (abgeschnitten?)"
                        parts.append(Partition(logical_index, "MBR logisch", lba, n, f"0x{t:02X}",
                                               sector_size=ss, warning=warning))
                        logical_index += 1
                next_entries = [(rel, n) for _, t, rel, n in chain if t in EXTENDED_TYPES]
                if not next_entries:
                    break
                current = base + next_entries[0][0]
            if len(visited) >= 256:
                report.warnings.append("Erweiterte MBR-Partitionskette bei 256 Einträgen begrenzt.")
            continue
        if start == 0 or start * ss >= size:
            continue
        warning = "" if (start + count) * ss <= size else "Partition größer als Image (abgeschnitten?)"
        parts.append(Partition(number, "MBR", start, count, f"0x{typ:02X}",
                               sector_size=ss, warning=warning))
    return parts, has_protective


def _read_gpt(f, size: int, ss: int, at_lba: int, backup: bool) -> tuple[list[Partition], str, str] | None:
    """Return (entries, crc_warning, label) when a plausible GPT is at at_lba."""
    offset = at_lba * ss
    if offset < 0 or offset + ss > size:
        return None
    hdr = _read_at(f, offset, ss)
    if hdr[:8] != b"EFI PART":
        return None
    header_size = struct.unpack_from("<I", hdr, 12)[0]
    if not 92 <= header_size <= ss:
        return None
    current, other, usable_first, usable_last = struct.unpack_from("<QQQQ", hdr, 24)
    entry_lba = struct.unpack_from("<Q", hdr, 72)[0]
    count, item_size, entry_crc = struct.unpack_from("<III", hdr, 80)
    if (current != at_lba or other == current or
            not (1 <= count <= 16384 and 128 <= item_size <= 1024 and item_size % 8 == 0) or
            usable_first > usable_last):
        return None
    amount = count * item_size
    if entry_lba * ss + amount > size:
        return None
    entries_blob = _read_at(f, entry_lba * ss, amount)
    if len(entries_blob) != amount:
        return None
    expected_hdr_crc = struct.unpack_from("<I", hdr, 16)[0]
    temp = bytearray(hdr[:header_size])
    temp[16:20] = bytes(4)
    header_ok = zlib.crc32(temp) == expected_hdr_crc
    entries_ok = zlib.crc32(entries_blob) == entry_crc
    warning = "" if header_ok and entries_ok else "GPT-CRC fehlerhaft – Einträge nur als Kandidaten behandeln"
    label = "GPT Backup" if backup else "GPT primär"
    partitions = []
    for i in range(count):
        ent = entries_blob[i*item_size:(i+1)*item_size]
        if ent[:16] == bytes(16):
            continue
        first, last = struct.unpack_from("<QQ", ent, 32)
        if first == 0 or last < first or first > (size + ss - 1) // ss:
            continue
        try:
            name = ent[56:min(item_size, 128)].decode("utf-16le", "replace").rstrip("\0")
        except Exception:
            name = ""
        part_warning = warning
        if last * ss >= size:
            part_warning = (part_warning + "; " if part_warning else "") + "Partition größer als Image"
        partitions.append(Partition(i+1, label, first, last-first+1,
                                     ent[:16].hex(), name, ss, warning=part_warning))
    return partitions, warning, label


def _detect_filesystem(f, pos: int, size: int):
    """Return (filesystem, sectors, bytes_per_sector, warning) for validated VBR."""
    if pos < 0 or pos + 512 > size:
        return None
    # XFS v4/v5: the big-endian superblock starts at the volume offset.
    xfs = _read_at(f, pos, 512)
    if len(xfs) == 512 and xfs[:4] == b'XFSB':
        block = struct.unpack_from('>I', xfs, 4)[0]
        blocks = struct.unpack_from('>Q', xfs, 8)[0]
        agblocks = struct.unpack_from('>I', xfs, 84)[0]
        agcount = struct.unpack_from('>I', xfs, 88)[0]
        inode_size = struct.unpack_from('>H', xfs, 104)[0]
        if block in (512, 1024, 2048, 4096, 8192, 16384, 32768, 65536) and blocks >= 4 and agblocks > 0 and agcount > 0 and inode_size in (256, 512, 1024, 2048):
            total = block * blocks
            warn = 'XFS-Volume reicht über Image-Ende' if pos+total > size else ''
            return 'XFS', (total+511)//512, 512, warn
    # Btrfs primary superblock at volume offset +64 KiB.
    # Unsupported RAID profiles are *only* detected here, not decoded/exported.
    if pos + 65536 + 4096 <= size:
        sup = _read_at(f, pos+65536, 4096)
        if len(sup)==4096 and sup[0x40:0x48]==b'_BHRfS_M':
            total=struct.unpack_from('<Q',sup,0x70)[0]
            sectorsize=struct.unpack_from('<I',sup,0x90)[0]
            nodesize=struct.unpack_from('<I',sup,0x94)[0]
            num_devices=struct.unpack_from('<Q',sup,0x88)[0]
            if 128*1024 <= total and sectorsize in (4096,8192,16384,32768,65536) and nodesize in (4096,8192,16384,32768,65536) and num_devices>0:
                warnings=[]
                if pos+total>size:warnings.append('Btrfs-Volume reicht über Image-Ende')
                if num_devices>1:warnings.append('Btrfs Mehrgeräte-Dateisystem: Browsing nicht verfügbar')
                return 'Btrfs',(total+511)//512,512,'; '.join(warnings)
    # Linux ext superblock is at partition-relative byte 1024, and its magic at +1080.
    # Unlike FAT/NTFS, ext does not require a boot-sector signature at pos.
    if pos + 2048 <= size:
        sb = _read_at(f, pos + 1024, 1024)
        if len(sb) == 1024 and sb[56:58] == b'\x53\xef':
            blocks = struct.unpack_from('<I', sb, 4)[0]
            log_block = struct.unpack_from('<I', sb, 24)[0]
            inodes = struct.unpack_from('<I', sb, 0)[0]
            ipg = struct.unpack_from('<I', sb, 40)[0]
            bpg = struct.unpack_from('<I', sb, 32)[0]
            incompat = struct.unpack_from('<I', sb, 96)[0]
            compat = struct.unpack_from('<I', sb, 92)[0]
            if blocks >= 2 and 0 <= log_block <= 6 and inodes >= 2 and ipg > 0 and bpg > 0:
                if incompat & 0x80:
                    blocks |= struct.unpack_from('<I', sb, 0x150)[0] << 32
                blocksize = 1024 << log_block
                fs = 'ext4' if incompat & (0x40|0x80|0x200) else 'ext3' if compat & 4 else 'ext2'
                total_bytes = blocks * blocksize
                if total_bytes > 0:
                    warning = ('Ext-Volume reicht über das Image-Ende' if pos + total_bytes > size else '')
                    return fs, (total_bytes+511)//512, 512, warning
    b = _read_at(f, pos, 512)
    if len(b) != 512 or b[510:512] != b"\x55\xaa" or b[0] not in (0xEB, 0xE9):
        return None
    signature = b[3:11]
    if signature == b"NTFS    ":
        bps = struct.unpack_from("<H", b, 11)[0]
        spc = b[13]
        sectors = struct.unpack_from("<Q", b, 40)[0]
        mft_lcn = struct.unpack_from("<Q", b, 48)[0]
        clusters_per_file_record = struct.unpack_from("<b", b, 64)[0]
        if bps not in (512, 1024, 2048, 4096) or spc == 0 or spc & (spc-1) or spc > 128 or sectors == 0:
            return None
        if not clusters_per_file_record or mft_lcn * bps * spc >= sectors * bps:
            return None
        fs = "NTFS"
    elif signature == b"EXFAT   ":
        bps_shift, spc_shift = b[108], b[109]
        if not (9 <= bps_shift <= 12 and spc_shift <= 16 and b[11:64] == bytes(53)):
            return None
        bps = 1 << bps_shift
        sectors = struct.unpack_from("<Q", b, 72)[0]
        fat_lba, fat_size, heap_lba, clusters, root = struct.unpack_from("<IIIII", b, 80)
        if not (sectors and fat_lba and fat_size and fat_lba < heap_lba < sectors and
                clusters >= 1 and 2 <= root <= clusters+1 and
                heap_lba + clusters * (1 << spc_shift) <= sectors):
            return None
        fs = "exFAT"
    elif b[82:90] == b"FAT32   ":
        bps = struct.unpack_from("<H", b, 11)[0]
        spc = b[13]
        reserved, fats = struct.unpack_from("<HB", b, 14)
        sectors = struct.unpack_from("<I", b, 32)[0]
        fat_size = struct.unpack_from("<I", b, 36)[0]
        root = struct.unpack_from("<I", b, 44)[0]
        if (bps not in (512, 1024, 2048, 4096) or spc == 0 or spc & (spc-1) or
                not reserved or fats not in (1, 2) or not sectors or not fat_size or root < 2 or
                reserved + fats * fat_size >= sectors):
            return None
        fs = "FAT32"
    elif signature == b"-FVE-FS-":
        bps = struct.unpack_from("<H", b, 11)[0]
        if bps not in (512, 1024, 2048, 4096):
            return None
        sectors = max(1, (size - pos) // bps)
        fs = "BitLocker"
    else:
        return None
    warning = ""
    if pos + sectors * bps > size:
        warning = "Volumestruktur reicht über Image-Ende (Abbild evtl. unvollständig)"
    if fs == "BitLocker":
        warning = "BitLocker: verschlüsselt, Entsperren außerhalb von RecoveryDesk nötig"
    return fs, sectors, bps, warning


def _scan_offsets(f, size: int, scan_bytes: int, progress: Callable[[int, int], None] | None = None):
    """Scan aligned on-disk boot signatures, including occurrences across chunk boundaries."""
    chunk_size = 4 * 1024 * 1024
    overlap = 1100
    offset, tail = 0, b""
    emitted = set()
    signatures = ((b"NTFS    ", 3), (b"EXFAT   ", 3), (b"-FVE-FS-", 3), (b"FAT32   ", 82), (b"\x53\xef", 1080), (b"XFSB", 0), (b"_BHRfS_M", 65536+0x40))
    while offset < scan_bytes:
        f.seek(offset)
        data = f.read(min(chunk_size, scan_bytes-offset))
        if not data:
            break
        combined = tail + data
        base = offset - len(tail)
        for sig, displacement in signatures:
            start = 0
            while True:
                i = combined.find(sig, start)
                if i < 0:
                    break
                pos = base + i - displacement
                if pos >= 0 and pos % 512 == 0 and pos not in emitted:
                    emitted.add(pos)
                    yield pos
                start = i + 1
        tail = combined[-overlap:]
        offset += len(data)
        if progress:
            progress(offset, scan_bytes)


def _ntfs_backup_origin(f, backup_at: int, image_size: int) -> int | None:
    """In a deep scan, detect an NTFS *backup* VBR and infer its partition start.

    A recovered offset is only offered when a valid $MFT FILE record confirms
    the volume geometry. It is a candidate, never an instruction to rewrite
    the missing primary VBR, and browsing may remain unavailable.
    """
    boot = _read_at(f, backup_at, 512)
    if len(boot) != 512 or boot[3:11] != b"NTFS    " or boot[510:512] != b"\x55\xaa":
        return None
    bps = struct.unpack_from('<H', boot, 11)[0]
    spc = boot[13]
    total = struct.unpack_from('<Q', boot, 40)[0]
    mft_lcn = struct.unpack_from('<Q', boot, 48)[0]
    if bps not in (512, 1024, 2048, 4096) or not total or not spc:
        return None
    volume_bytes = total * bps
    start = backup_at - volume_bytes + bps
    if start < 0 or start % 512 or start + volume_bytes > image_size:
        return None
    if _detect_filesystem(f, start, image_size) is not None:
        return None  # Primary boot sector exists; do not duplicate it.
    mft_offset = start + mft_lcn * bps * spc
    if mft_offset < start or mft_offset + 4 > backup_at or mft_offset + 4 > image_size:
        return None
    if _read_at(f, mft_offset, 4) != b'FILE':
        return None
    return start


def _validate_candidates(f, report: AnalysisReport, image_size: int) -> None:
    """Annotate evidence and metadata conflicts without altering disk bytes.

    Qualitative confidence describes available *metadata*, not probability of
    file recovery. Both confirmed partitions and candidates may be unreadable.
    """
    parts = report.partitions
    for p in parts:
        evidence = []
        candidate = p.scheme.startswith('Fund') or p.scheme == 'Volume'
        fs = _detect_filesystem(f, p.offset_bytes, image_size)
        is_copy = p.scheme == 'Fund (NTFS-Kopie)'
        if p.scheme.startswith('GPT'):
            evidence.append('GPT-Partitionseintrag vorhanden')
            evidence.append('GPT-CRC fehlerhaft' if 'CRC' in p.warning else 'GPT-Prüfsummen bestätigt')
        elif p.scheme.startswith('MBR'):
            evidence.append('MBR-Partitionseintrag vorhanden (ohne Prüfsumme)')
        elif is_copy:
            evidence.append('NTFS-Backup-Bootsektor und $MFT-Signatur passen geometrisch zusammen')
        else:
            evidence.append('Dateisystemsignatur ohne bestätigte Partitionstabelle')
        if fs:
            evidence.append(f'Plausibler {fs[0]}-Dateisystemanfang')
            volume_size = fs[1] * fs[2]
            # A filesystem smaller than its table entry may simply be intentional.
            # A larger filesystem, however, can make reads cross a partition border.
            if not candidate and volume_size > p.size_bytes + max(fs[2], 4096):
                p.warning = '; '.join(filter(None, (p.warning,
                    'Dateisystem meldet mehr Sektoren als die Partitionstabelle')))
                evidence.append('Widersprüchliche Größenangaben')
        elif not is_copy:
            evidence.append('Kein unterstützter Dateisystemanfang bestätigt')
        if p.offset_bytes + p.size_bytes > image_size:
            evidence.append('Volume reicht über die Quelle hinaus')
            if 'Image' not in p.warning and 'Volume' not in p.warning:
                p.warning = '; '.join(filter(None, (p.warning, 'Ende außerhalb der lesbaren Quelle')))
        if is_copy or 'CRC' in p.warning or 'Widersprüchliche' in ' '.join(evidence) or 'über die Quelle' in ' '.join(evidence):
            p.confidence = 'Niedrig'
        elif p.scheme.startswith('GPT') and fs is not None:
            p.confidence = 'Hoch'
        elif p.scheme.startswith('GPT') or fs is not None:
            p.confidence = 'Mittel'
        else:
            p.confidence = 'Niedrig'
        if p.scheme.startswith('GPT') and any('unterschiedliche Partitionen' in w for w in report.warnings):
            p.confidence = 'Niedrig'
            evidence.append('Primäre und Backup-GPT widersprechen sich')
        p.evidence = evidence

    # Cross-check partition boundaries. Overlap is an alert, never automatically
    # merged or discarded: some nested signatures can be false positives.
    ordered = sorted((p for p in parts if p.size_bytes > 0), key=lambda p: p.offset_bytes)
    for i, left in enumerate(ordered):
        end = left.offset_bytes + left.size_bytes
        for right in ordered[i+1:]:
            if right.offset_bytes >= end:
                break
            if left is right:
                continue
            marker = 'Überlappende Bereiche mit anderem Partitionsfund'
            for part in (left, right):
                if marker not in part.warning:
                    part.warning = '; '.join(filter(None, (part.warning, marker)))
                    part.evidence.append('Partitionsbereiche überlappen')
                part.confidence = 'Niedrig'
            warning = (f'Überlappung: Offset {left.offset_bytes:,} und '
                       f'{right.offset_bytes:,} Byte. Einträge vor dem Öffnen vergleichen.')
            if warning not in report.warnings:
                report.warnings.append(warning)

def analyze_image(path: str, deep_scan: bool = False, max_scan_mb: int = 4096,
                  sector_size: int | str = "auto",
                  progress: Callable[[int, int], None] | None = None) -> AnalysisReport:
    """Analyze RAW disk/volume image incl. NTFS/exFAT/FAT32 and Linux ext superblocks.

    deep_scan=False scans the first 64 MiB for validated boot sectors; deep_scan=True
    scans up to max_scan_mb MiB, or the whole image when max_scan_mb=0.
    Only normal files are accepted; source opened 'rb' and never modified.
    """
    sizes = _valid_sector_size(sector_size)
    if max_scan_mb < 0 or max_scan_mb > 1_048_576:
        raise ValueError("Das Suchlimit muss 0 bis 1.048.576 MiB betragen.")
    size = source_size(path)
    report = AnalysisReport(size)
    if size < 512:
        report.warnings.append("Image kleiner als ein Sektor. Kein RAW-Laufwerksabbild erkennbar.")
        return report
    selected_parts = []
    with open_source(path) as f:
        gpt = []
        mbr = []
        mbr_score = -1
        mbr_protective = False
        for ss in sizes:
            gpt_primary = _read_gpt(f, size, ss, 1, False)
            backup_lba = size // ss - 1 if size % ss == 0 else -1
            gpt_backup = _read_gpt(f, size, ss, backup_lba, True) if backup_lba > 1 else None
            for candidate in (gpt_primary, gpt_backup):
                if candidate and candidate[1]:
                    report.warnings.append(f"{candidate[2]} mit {ss}-Byte-Sektoren: {candidate[1]}.")
            if gpt_primary or gpt_backup:
                best = gpt_primary if gpt_primary and not gpt_primary[1] else gpt_backup if gpt_backup and not gpt_backup[1] else gpt_primary or gpt_backup
                if best and (not gpt or (gpt[1] and not best[1])):
                    gpt = [best[0], best[1], ss]
                if gpt_primary and gpt_backup and [(p.offset_bytes, p.size_bytes) for p in gpt_primary[0]] != [(p.offset_bytes, p.size_bytes) for p in gpt_backup[0]]:
                    report.warnings.append("Primäre und Backup-GPT enthalten unterschiedliche Partitionen.")
            mbr_parts, protective = _read_mbr(f, size, ss, report)
            mbr_protective |= protective
            if mbr_parts:
                # MBR has no sector-size field: prefer the interpretation that
                # points to structurally valid filesystem boot sectors.
                score = sum(1 for part in mbr_parts
                            if _detect_filesystem(f, part.offset_bytes, size))
                if score > mbr_score:
                    mbr_score = score
                    mbr = mbr_parts
        if gpt:
            selected_parts = gpt[0]
            report.sector_size = gpt[2]
            report.table_type = "GPT"
        elif mbr:
            selected_parts = mbr
            report.sector_size = mbr[0].sector_size
            report.table_type = "MBR"
            if mbr_protective:
                report.warnings.append("Schutz-MBR ohne lesbare GPT; MBR-Einträge könnten veraltet sein.")
        elif mbr_protective:
            report.warnings.append("Schutz-MBR (0xEE) vorhanden, aber keine auswertbare primäre/Backup-GPT erkannt.")
        report.partitions = selected_parts
        known = {p.offset_bytes for p in selected_parts}
        for p in selected_parts:
            found = _detect_filesystem(f, p.offset_bytes, size)
            if found:
                p.filesystem = found[0]
                if found[3]:
                    p.warning = "; ".join(filter(None, (p.warning, found[3])))
        scan_limit = min(size, (max_scan_mb * 1024 * 1024 if deep_scan and max_scan_mb else
                                size if deep_scan else 64 * 1024 * 1024))
        for offset in _scan_offsets(f, size, scan_limit, progress):
            match = _detect_filesystem(f, offset, size)
            if not match:
                continue
            filesystem, sectors, bps, warning = match
            if deep_scan and filesystem == 'NTFS' and offset not in known:
                backup_start = _ntfs_backup_origin(f, offset, size)
                if backup_start is not None:
                    matching = next((p for p in report.partitions
                                     if p.offset_bytes == backup_start), None)
                    hint = ('Primärer NTFS-Bootsektor fehlt; Beginn aus Backup-Bootsektor '
                            'und MFT-Signatur abgeleitet. Nicht automatisch reparieren.')
                    if matching is not None:
                        matching.filesystem = 'NTFS'
                        matching.warning = '; '.join(filter(None, (matching.warning, hint)))
                    else:
                        report.partitions.append(Partition(
                            len(report.partitions)+1, 'Fund (NTFS-Kopie)',
                            backup_start//512, (sectors*bps+511)//512,
                            'NTFS-Backup', 'NTFS-Bootkopie', 512, 'NTFS', hint))
                        known.add(backup_start)
                    known.add(offset)
                    continue
            if offset in known:
                # A recognized filesystem at a table entry was already annotated.
                continue
            # NTFS has an optional VBR copy in its last sector; exFAT stores
            # a backup boot region starting 12 sectors after its main VBR.
            # Neither should be reported as a separate partition.
            if any((p.filesystem == filesystem and p.size_bytes > 0 and
                    ((filesystem == "NTFS" and
                      offset == p.offset_bytes + p.size_bytes - bps) or
                     (filesystem == "exFAT" and
                      offset == p.offset_bytes + 12*bps)))
                   for p in report.partitions):
                continue
            if (filesystem == "BitLocker" and offset != 0 and not deep_scan):
                continue
            scheme = "Volume" if offset == 0 else "Fund (VBR)"
            report.partitions.append(Partition(len(report.partitions)+1, scheme,
                                 offset // 512, (sectors * bps + 511) // 512,
                                 filesystem, filesystem, 512, filesystem,
                                 "; ".join(filter(None, ("Heuristischer Fund; kein Beweis für eine gültige Partition", warning)))))
            known.add(offset)
        report.scanned_bytes = scan_limit
        if report.table_type == "keine":
            report.warnings.append("Keine gültige MBR/GPT-Partitionstabelle erkannt. Dateisystem-Funde sind nur Kandidaten.")
        if scan_limit < size:
            report.warnings.append(f"Dateisystemsuche auf die ersten {scan_limit / 1024**2:.0f} MiB begrenzt; Tiefensuche für weitere Bereiche verwenden.")
        if not report.partitions:
            report.warnings.append("Keine unterstützte Struktur gefunden. Möglich: verschlüsselt, anderes Dateisystem, komprimiertes Image oder beschädigte Metadaten.")
        if report.table_type == "GPT" and gpt and gpt[1]:
            report.warnings.append("GPT-Struktur beschädigt: gefundene Einträge nicht für Partitionsschreibvorgänge verwenden.")
        _validate_candidates(f, report, size)
    return report



def format_partition_findings(source: str, report: AnalysisReport) -> str:
    """Plain-text report of all candidates, including unverified findings.

    No attempt is made to repair structures or infer missing file contents.
    """
    lines = [
        'Tenshi – Partitionsfunde (nur lesende Analyse)',
        f'Quelle: {source}',
        f'Quellgröße: {report.image_size:,} Bytes',
        f'Partitionsschema: {report.table_type}',
        f'Logische Sektorgröße: {report.sector_size} Bytes',
        f'Durchsucht: {report.scanned_bytes:,} Bytes',
        f'Anzahl Funde: {len(report.partitions)}',
        '',
        'Plausibilität beschreibt Metadaten, nicht die Wahrscheinlichkeit einer Datenrettung.',
        'Es wurden keine Partitions- oder Dateisystemdaten repariert.',
    ]
    for part in report.partitions:
        lines.extend((
            '', f'[{part.index}] {part.scheme} / {part.filesystem}',
            f'  Plausibilität: {part.confidence}',
            f'  Start: {part.offset_bytes:,} Bytes',
            f'  Länge: {part.size_bytes:,} Bytes',
            f'  Name: {part.name or "—"}',
            f'  Typ/GUID: {part.type_code}',
        ))
        if part.warning:
            lines.append(f'  Warnung: {part.warning}')
        for item in part.evidence:
            lines.append('  Hinweis: ' + item)
    if report.warnings:
        lines.extend(('', 'Allgemeine Hinweise:'))
        lines.extend('- ' + item for item in report.warnings)
    return '\n'.join(lines) + '\n'


def scan_partitions(path: str, max_bytes: int | None = None) -> list[Partition]:
    """Backwards-compatible read-only list of partitions/candidate filesystems.
    max_bytes (if passed) limits filesystem signature scan, not GPT metadata reading.
    """
    if max_bytes is None:
        return analyze_image(path).partitions
    if max_bytes < 0:
        raise ValueError("max_bytes darf nicht negativ sein")
    # Keep public API simple; this function is used in the old application.
    return analyze_image(path, deep_scan=True, max_scan_mb=max(1, (max_bytes + 1024**2 - 1)//1024**2)).partitions
