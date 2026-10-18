"""Conservative recovery from surviving FAT links in deleted file records.
All fixtures are synthetic. The original image is never modified by Tenshi.
"""
import struct
import tempfile
import unittest
from pathlib import Path

from recoverydesk.filesystems import FileSystemError, scan_tree, export_file


def fat32_fragmented(*, reuse=None, break_mirror=False, mirroring_enabled=True, offset=0):
    bps, reserved, fat_sectors, sectors, fats = 512, 32, 4, 512, 2
    data_sector = reserved + fats * fat_sectors
    image = bytearray(offset + sectors * bps)
    boot = bytearray(512)
    boot[82:90] = b'FAT32   '
    struct.pack_into('<H', boot, 11, bps)
    boot[13] = 1
    struct.pack_into('<H', boot, 14, reserved)
    boot[16] = fats
    struct.pack_into('<I', boot, 32, sectors)
    struct.pack_into('<I', boot, 36, fat_sectors)
    struct.pack_into('<I', boot, 44, 2)
    if not mirroring_enabled:
        struct.pack_into('<H', boot, 40, 0x0080)
    boot[510:512] = b'\x55\xaa'
    image[offset:offset+512] = boot
    fat0 = offset + reserved*bps
    fat1 = fat0 + fat_sectors*bps
    for p in (fat0, fat1):
        for c, val in ((0, 0x0FFFFFF8), (1, 0x0FFFFFFF), (2, 0x0FFFFFFF)):
            struct.pack_into('<I', image, p+c*4, val)
    struct.pack_into('<I', image, fat1 + 5*4, 9 if not break_mirror else 0x0FFFFFF7)
    struct.pack_into('<I', image, fat1 + 9*4, 0x0FFFFFFF)
    if reuse is not None:
        struct.pack_into('<I', image, fat0 + reuse*4, 0x0FFFFFFF)
    data_off = offset + data_sector*bps
    row = bytearray(32)
    row[:11] = b'\xe5RAG    BIN'
    row[11] = 0x20
    struct.pack_into('<H', row, 26, 5)
    struct.pack_into('<I', row, 28, 700)
    image[data_off:data_off+32] = row
    image[data_off+32] = 0
    def cl(n): return offset+(data_sector+n-2)*bps
    image[cl(5):cl(5)+512] = b'A'*512
    image[cl(9):cl(9)+188] = b'B'*188
    image[cl(6):cl(6)+188] = b'X'*188
    return bytes(image)


def exfat_fragmented(*, reuse=None, break_chain=False, cyclic=False, offset=0):
    image = bytearray(offset + 512*256)
    boot = bytearray(512)
    boot[3:11] = b'EXFAT   '
    boot[108] = 9
    boot[109] = 0
    boot[110] = 1
    struct.pack_into('<Q', boot, 72, 256)
    struct.pack_into('<I', boot, 80, 24)
    struct.pack_into('<I', boot, 84, 2)
    struct.pack_into('<I', boot, 88, 32)
    struct.pack_into('<I', boot, 92, 120)
    struct.pack_into('<I', boot, 96, 2)
    boot[510:512] = b'\x55\xaa'
    image[offset:offset+512] = boot
    def cl(n): return offset + (32 + n - 2)*512
    fat = offset + 24*512
    struct.pack_into('<I', image, fat + 2*4, 0xFFFFFFFF)
    struct.pack_into('<I', image, fat + 3*4, 0xFFFFFFFF)
    struct.pack_into('<I', image, fat + 5*4, 0 if break_chain else 9)
    struct.pack_into('<I', image, fat + 9*4, 5 if cyclic else 0xFFFFFFFF)
    bitmap = bytearray(32)
    bitmap[0] = 0x81
    struct.pack_into('<I', bitmap, 20, 3)
    struct.pack_into('<Q', bitmap, 24, 15)
    image[cl(2):cl(2)+32] = bitmap
    primary = bytearray(32)
    primary[0] = 0x05
    primary[1] = 2
    stream = bytearray(32)
    stream[0] = 0x40
    stream[1] = 0  # FAT chain, NOT NoFatChain contiguous
    stream[3] = 8
    struct.pack_into('<I', stream, 20, 5)
    struct.pack_into('<Q', stream, 8, 700)
    struct.pack_into('<Q', stream, 24, 700)
    name = bytearray(32)
    name[0] = 0x41
    name[2:18] = 'frag.bin'.encode('utf-16le')
    image[cl(2)+32:cl(2)+64] = primary
    image[cl(2)+64:cl(2)+96] = stream
    image[cl(2)+96:cl(2)+128] = name
    image[cl(2)+128] = 0
    # Cluster 2 (root) and 3 (bitmap) used. Deleted 5 and 9 free.
    image[cl(3)] = 0b00000011 | ((1 << (reuse-2)) if reuse is not None and reuse <= 9 else 0)
    image[cl(3)+1] = (1 << (reuse-10)) if reuse is not None and reuse >= 10 else 0
    image[cl(5):cl(5)+512] = b'A'*512
    image[cl(9):cl(9)+188] = b'B'*188
    image[cl(6):cl(6)+188] = b'X'*188
    return bytes(image)


class DeletedFragmentedTests(unittest.TestCase):
    def _read_export(self, image, offset=0):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'source.img'
            source.write_bytes(image)
            index = scan_tree(str(source), offset)
            entries = index.list_dir(5)
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertTrue(entry.is_deleted)
            if entry.recoverable:
                dest = Path(d)/'rescued.bin'
                n = export_file(str(source), index, entry, str(dest))
                self.assertEqual(n,700)
                self.assertEqual(dest.read_bytes(), b'A'*512 + b'B'*188)
                self.assertEqual(source.read_bytes(), image)
            return entry.recoverable, entry.unsupported_reason

    def test_exfat_fragmented_chain(self):
        for offset in (0, 4096):
            ok, reason = self._read_export(exfat_fragmented(offset=offset),offset)
            self.assertTrue(ok,reason)

    def test_fat32_mirror_fragmented_chain(self):
        for offset in (0, 4096):
            ok, reason = self._read_export(fat32_fragmented(offset=offset),offset)
            self.assertTrue(ok,reason)

    def test_exfat_reused_cluster_refused_at_scan(self):
        for cluster in (5,9):
            ok, reason = self._read_export(exfat_fragmented(reuse=cluster))
            self.assertFalse(ok)

    def test_fat32_reused_cluster_refused_at_scan(self):
        for cluster in (5,9):
            ok, reason = self._read_export(fat32_fragmented(reuse=cluster))
            self.assertFalse(ok)

    def test_exfat_missing_or_cyclic_chain_refused(self):
        for kwargs in ({'break_chain':True}, {'cyclic':True}):
            ok, reason = self._read_export(exfat_fragmented(**kwargs))
            self.assertFalse(ok)

    def test_fat32_broken_mirror_or_disabled_mirroring_refused(self):
        for kwargs in ({'break_mirror':True}, {'mirroring_enabled':False}):
            ok, reason = self._read_export(fat32_fragmented(**kwargs))
            # Contiguous recovery is still hypothesized if all FAT copies are zero.
            self.assertFalse(ok)

    def test_exfat_rechecks_all_bitmap_bits_before_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.img';p.write_bytes(exfat_fragmented())
            index=scan_tree(str(p));e=index.list_dir(5)[0]
            self.assertTrue(e.recoverable)
            with p.open('r+b') as f:
                f.seek((32+3-2)*512+0)
                f.write(bytes([0b10000011]))  # cluster 9 is allocated
            output=Path(d)/'no.bin'
            with self.assertRaises(FileSystemError):
                export_file(str(p),index,e,str(output))
            self.assertFalse(output.exists())

    def test_exfat_rechecks_saved_fat_chain_before_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.img';p.write_bytes(exfat_fragmented())
            index=scan_tree(str(p));e=index.list_dir(5)[0]
            with p.open('r+b') as f:
                f.seek(24*512+5*4)
                f.write(struct.pack('<I',8))
            output=Path(d)/'no.bin'
            with self.assertRaises(FileSystemError):
                export_file(str(p),index,e,str(output))
            self.assertFalse(output.exists())

    def test_fat32_rechecks_mirror_chain_before_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.img';p.write_bytes(fat32_fragmented())
            index=scan_tree(str(p));e=index.list_dir(5)[0]
            with p.open('r+b') as f:
                f.seek((32+4)*512 + 5*4)
                f.write(struct.pack('<I',8))
            output=Path(d)/'no.bin'
            with self.assertRaises(FileSystemError):
                export_file(str(p),index,e,str(output))
            self.assertFalse(output.exists())

    def test_fat32_rechecks_primary_fat_before_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.img';p.write_bytes(fat32_fragmented())
            index=scan_tree(str(p));e=index.list_dir(5)[0]
            with p.open('r+b') as f:
                f.seek(32*512+9*4)
                f.write(struct.pack('<I',0x0FFFFFFF))
            output=Path(d)/'no.bin'
            with self.assertRaises(FileSystemError):
                export_file(str(p),index,e,str(output))
            self.assertFalse(output.exists())

if __name__ == '__main__':
    unittest.main()
