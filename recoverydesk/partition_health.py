"""Bounded, read-only superblock diagnostics; deliberately NOT a filesystem check.

Usage counters are *metadata-reported*, not derived from a full allocation scan.
They can be stale/corrupt and must never be presented as verified free space.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import struct
from .partition_scan import Partition
from .sources import open_source, source_size
from .ntfs_usage import inspect_ntfs_bitmap, BitmapUnavailable


@dataclass
class PartitionDetails:
    filesystem: str
    offset: int
    partition_bytes: int
    volume_bytes: int | None = None
    used_bytes: int | None = None
    free_bytes: int | None = None
    usage_basis: str = 'Nicht verfügbar'
    status: str = 'Nicht geprüft'
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def used_percent(self) -> float | None:
        if self.used_bytes is None or not self.volume_bytes:
            return None
        return max(0., min(100., self.used_bytes * 100. / self.volume_bytes))


def _read(f, offset, count, limit):
    if count < 0 or offset < 0 or offset + count > limit:
        raise ValueError('Metadaten liegen außerhalb des lesbaren Datenträgers.')
    f.seek(offset)
    b = f.read(count)
    if len(b) != count:
        raise OSError('Metadaten konnten nicht vollständig gelesen werden.')
    return b


def _u16(b, off): return struct.unpack_from('<H', b, off)[0]
def _u32(b, off): return struct.unpack_from('<I', b, off)[0]
def _u64(b, off): return struct.unpack_from('<Q', b, off)[0]


def inspect_partition(path: str, part: Partition) -> PartitionDetails:
    """Inspect one chosen partition using small, bounded read-only requests.

    No writes, no hardware retries, no free-cluster walking. File-system
    utilization can only be computed when a trustworthy *format* and plausible
    superblock counters are available; accuracy of counters is NOT established.
    """
    limit = source_size(path)
    off = part.offset_bytes
    d = PartitionDetails(part.filesystem, off, part.size_bytes)
    if part.warning:
        d.warnings.append(part.warning)
    if off < 0 or off >= limit:
        d.warnings.append('Partitionsbeginn liegt außerhalb des Datenträgers.')
        d.status = 'Auffällig'
        return d
    if off + part.size_bytes > limit:
        d.warnings.append('Partitionsende liegt außerhalb der lesbaren Quelle.')
    if part.scheme.startswith('Fund') or part.scheme == 'Volume':
        d.notes.append('Bootsektor-Fund ohne bestätigte Partitionstabelle; Position verifizieren.')
    try:
        with open_source(path) as f:
            fs = part.filesystem.casefold()
            if fs == 'ntfs':
                b = _read(f, off, 512, limit)
                if b[3:11] != b'NTFS    ' or b[510:512] != b'\x55\xaa':
                    raise ValueError('NTFS-Signatur oder Bootsektor-Abschluss fehlt.')
                bps = _u16(b, 11)
                spc = b[13]
                count = _u64(b, 40)
                if bps not in (512,1024,2048,4096) or spc == 0 or spc & (spc-1) or count == 0:
                    raise ValueError('NTFS-Sektor- oder Clustergeometrie ist unplausibel.')
                d.volume_bytes = count * bps
                try:
                    usage = inspect_ntfs_bitmap(f, off)
                except BitmapUnavailable as exc:
                    d.notes.append('NTFS-Belegung unbekannt: $Bitmap nicht vollständig auswertbar (' + str(exc) + ').')
                else:
                    d.volume_bytes = usage.capacity_bytes
                    d.used_bytes = usage.used_bytes
                    d.free_bytes = usage.free_bytes
                    d.usage_basis = 'NTFS $Bitmap: belegte Clusterbits, vollständiger Datenstrom; kein Integritätsnachweis'
                    d.notes.append('NTFS: Bitmap-Zähler berücksichtigt Cluster, nicht ausschließlich Nutzdateien.')
                    # Avoid silently presenting non-zero but implausible bitmap allocations.
                    if not usage.clusters_total:
                        d.warnings.append('NTFS meldet keine adressierbaren Cluster.')
            elif fs == 'fat32':
                b = _read(f, off, 512, limit)
                if b[82:90] != b'FAT32   ' or b[510:512] != b'\x55\xaa':
                    raise ValueError('FAT32-Bootsektor nicht plausibel.')
                bps, spc = _u16(b,11), b[13]
                reserved, fats = _u16(b,14), b[16]
                fat_sectors, total_sectors = _u32(b,36), _u32(b,32)
                if bps not in (512,1024,2048,4096) or spc == 0 or spc & (spc-1) or not reserved or not fats or not fat_sectors or not total_sectors:
                    raise ValueError('FAT32-Sektor- oder FAT-Geometrie unplausibel.')
                data_sectors = total_sectors - reserved - fats * fat_sectors
                if data_sectors <= 0:
                    raise ValueError('FAT32-Datenbereich ist ungültig.')
                clusters = data_sectors // spc
                d.volume_bytes = total_sectors * bps
                fsinfo_sector = _u16(b, 48)
                if 0 < fsinfo_sector < reserved and off + (fsinfo_sector+1)*bps <= limit:
                    info = _read(f, off+fsinfo_sector*bps, 512, limit)
                    valid = (_u32(info,0) == 0x41615252 and
                             _u32(info,484) == 0x61417272 and
                             _u32(info,508) == 0xAA550000)
                    if valid:
                        free_clusters = _u32(info,488)
                        if free_clusters == 0xFFFFFFFF:
                            d.notes.append('FAT32-FSInfo meldet keinen bekannten freien Clusterzähler.')
                        elif free_clusters <= clusters:
                            d.free_bytes = free_clusters * spc * bps
                            d.volume_bytes = clusters * spc * bps
                            d.used_bytes = d.volume_bytes - d.free_bytes
                            d.usage_basis = 'FAT32-FSInfo: möglicherweise veralteter Cachewert; nur Datenbereich'
                        else:
                            d.warnings.append('FAT32-FSInfo meldet unplausibel viele freie Cluster.')
                    else:
                        d.warnings.append('FAT32-FSInfo-Signaturen ungültig; kein Belegungswert.')
                else:
                    d.notes.append('Kein gültiger FAT32-FSInfo-Sektor adressierbar.')
            elif fs == 'exfat':
                b = _read(f, off, 512, limit)
                if b[3:11] != b'EXFAT   ' or b[510:512] != b'\x55\xaa':
                    raise ValueError('exFAT-Bootsektor nicht plausibel.')
                bps_shift, spc_shift = b[108], b[109]
                if not 9 <= bps_shift <= 12 or spc_shift > 25 - bps_shift:
                    raise ValueError('exFAT-Sektor- oder Clustergeometrie unplausibel.')
                bps = 1 << bps_shift
                cluster_bytes = bps << spc_shift
                count = _u32(b, 92)
                vol_sectors = _u64(b,72)
                if not count or not vol_sectors:
                    raise ValueError('exFAT-Volumengröße unplausibel.')
                d.volume_bytes = vol_sectors * bps
                volume_flags = _u16(b, 106)
                if volume_flags & 0x0002:
                    d.warnings.append('exFAT VolumeDirty-Flag gesetzt; Dateisystem wurde möglicherweise nicht sauber ausgehängt.')
                if volume_flags & 0x0004:
                    d.warnings.append('exFAT MediaFailure-Flag gesetzt; mögliches Medienproblem.')
                percent = b[112]
                if percent <= 100:
                    d.used_bytes = round(count * cluster_bytes * percent / 100)
                    d.free_bytes = count * cluster_bytes - d.used_bytes
                    d.volume_bytes = count * cluster_bytes
                    d.usage_basis = 'exFAT-PercentInUse (gerundet, evtl. veraltet); nur Clusterbereich'
                else:
                    d.notes.append('exFAT-PercentInUse ist unbekannt (0xFF).')
            elif fs in ('ext2','ext3','ext4'):
                sb = _read(f, off+1024, 1024, limit)
                if _u16(sb,56) != 0xEF53:
                    raise ValueError('Ext-Superblock-Signatur fehlt.')
                log_block = _u32(sb,24)
                incompat = _u32(sb,96)
                if log_block > 6:
                    raise ValueError('Ext-Blockgröße unplausibel.')
                block_size = 1024 << log_block
                blocks = _u32(sb,4)
                free = _u32(sb,12)
                if incompat & 0x80:
                    blocks |= _u32(sb,0x150) << 32
                    free |= _u32(sb,0x158) << 32
                if not blocks:
                    raise ValueError('Ext-Blockzähler ist null.')
                d.volume_bytes = blocks * block_size
                if free <= blocks:
                    d.free_bytes = free * block_size
                    d.used_bytes = (blocks - free) * block_size
                    d.usage_basis = 'Ext-Superblock-Zähler; inklusive reservierter Blöcke, nicht verifiziert'
                else:
                    d.warnings.append('Ext-Superblock meldet mehr freie als gesamte Blöcke.')
                state = _u16(sb,58)
                if state & 0x2:
                    d.warnings.append('Ext-Superblock meldet erkannte Dateisystemfehler.')
                if not state & 0x1:
                    d.notes.append('Ext-Superblock meldet keinen sauber ausgehängten Zustand; kein Beweis für Schäden.')
            elif fs == 'btrfs':
                sb = _read(f, off+65536, 4096, limit)
                if sb[0x40:0x48] != b'_BHRfS_M':
                    raise ValueError('Btrfs-Superblock-Signatur fehlt.')
                total, used = _u64(sb,0x70), _u64(sb,0x78)
                if not total:
                    raise ValueError('Btrfs-Volumengröße ist null.')
                d.volume_bytes = total
                if used <= total:
                    d.used_bytes = used
                    d.free_bytes = total-used
                    d.usage_basis = 'Btrfs-Superblock: belegte Bytes, keine nutzbare freie Kapazität'
                else:
                    d.warnings.append('Btrfs meldet mehr belegte Bytes als Volumegröße.')
                if _u64(sb,0x88) != 1:
                    d.warnings.append('Btrfs-Mehrgeräte-Volume: Einzelgerätanalyse nicht ausreichend.')
            elif fs == 'xfs':
                sb = _read(f, off, 512, limit)
                if sb[:4] != b'XFSB':
                    raise ValueError('XFS-Superblock-Signatur fehlt.')
                block_size = struct.unpack_from('>I',sb,4)[0]
                blocks = struct.unpack_from('>Q',sb,8)[0]
                free = struct.unpack_from('>Q',sb,144)[0]
                if block_size not in (512,1024,2048,4096,8192,16384,32768,65536) or not blocks:
                    raise ValueError('XFS-Blockgeometrie unplausibel.')
                d.volume_bytes = blocks*block_size
                if free <= blocks:
                    d.free_bytes = free*block_size
                    d.used_bytes = (blocks-free)*block_size
                    d.usage_basis = 'XFS-Superblock fdblocks; keine Prüfung durch Dateisystem-Scan'
                else:
                    d.warnings.append('XFS-Superblock meldet unplausibel viele freie Blöcke.')
                if sb[126]:
                    d.warnings.append('XFS meldet eine nicht abgeschlossene Dateisystem-Initialisierung.')
            else:
                d.notes.append('Für dieses Dateisystem sind keine Belegungszähler verfügbar.')
    except (OSError, ValueError, struct.error) as exc:
        d.warnings.append('Strukturprüfung nicht vollständig möglich: ' + str(exc))

    # Header may legitimately give a slightly different geometry than partition table.
    # Report only a material excess; on large sparse images this is useful context.
    if d.volume_bytes is not None:
        available = min(part.size_bytes, max(0, limit-off))
        if d.volume_bytes > available + max(1024*1024, available//100):
            d.warnings.append('Im Superblock gemeldete Volumegröße überschreitet den gewählten Bereich.')
    d.status = 'Auffällig' if d.warnings else 'Keine offensichtlichen Fehler'
    d.notes.append('Metadatenprüfung, kein chkdsk/fsck. Ein unauffälliges Ergebnis garantiert keine Datenintegrität.')
    return d


def format_partition_confidence(confidence: str, language: str = 'de') -> str:
    """Describe detection evidence without implying recovery odds or file health."""
    levels = {'Hoch': 'hohe Plausibilität', 'Mittel': 'mittlere Plausibilität',
              'Niedrig': 'geringe Plausibilität'}
    label = 'Partitionserkennung: ' + levels.get(confidence, confidence)
    scope = 'Diese Bewertung sagt nichts über den Zustand der Dateien oder die Rettungschancen aus.'
    if language != 'de':
        from .i18n import translate
        label, scope = translate(label, language), translate(scope, language)
    return label + '\n' + scope


def format_partition_details(part: Partition, details: PartitionDetails, source: str,
                             language: str = 'de') -> str:
    def amount(n):
        return 'unbekannt' if n is None else f'{n:,} Bytes ({n/1024**3:.3f} GiB)'
    rows = [
        'Tenshi – schreibgeschützter Partitionsbericht',
        f'Quelle: {source}',
        f'Partition: {part.index} / {part.scheme}',
        format_partition_confidence(part.confidence, language),
        *(('- ' + item) for item in part.evidence),
        f'Dateisystem: {details.filesystem}',
        f'Startoffset: {part.offset_bytes:,} Bytes',
        f'Partitionstabelle-Größe: {amount(part.size_bytes)}',
        f'Volumegröße (Metadaten): {amount(details.volume_bytes)}',
        f'Belegt (Metadaten): {amount(details.used_bytes)}',
        f'Frei (Metadaten): {amount(details.free_bytes)}',
        f'Zählermethode: {details.usage_basis}',
        f'Prüfstatus: {details.status}',
        '', 'Warnungen:',
        *(('- ' + s) for s in details.warnings),
        '' if details.warnings else '- Keine offensichtlichen Auffälligkeiten',
        '', 'Hinweise:',
        *(('- ' + s) for s in details.notes),
        '', 'Originalquelle nicht verändert.',
    ]
    return '\n'.join(rows) + '\n'
