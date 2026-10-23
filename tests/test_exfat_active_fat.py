"""Byte-level regressions for exFAT's active FAT and contradictory metadata."""
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import unittest

from recoverydesk.filesystems import ExFAT, FileSystemError, scan_tree, export_selection


def dual_fat_image(active=1, offset=0, contiguous=False, next_cluster=6):
    raw = bytearray(offset + 256 * 512)
    raw[offset + 3:offset + 11] = b'EXFAT   '
    raw[offset + 510:offset + 512] = b'\x55\xaa'
    struct.pack_into('<Q', raw, offset + 72, 256)
    struct.pack_into('<IIIII', raw, offset + 80, 24, 2, 32, 120, 2)
    struct.pack_into('<H', raw, offset + 106, active)
    raw[offset + 108:offset + 111] = bytes((9, 0, 2))
    for copy, file_next, root_next in ((0, 4, 8), (1, next_cluster, 7)):
        for cluster, value in ((2, root_next), (3, file_next), (4, 0xFFFFFFFF),
                               (6, 0xFFFFFFFF), (7, 0xFFFFFFFF), (8, 0xFFFFFFFF),
                               (9, 0xFFFFFFFF), (10, 0xFFFFFFFF)):
            struct.pack_into('<I', raw, offset + (24 + copy * 2) * 512 + cluster * 4, value)

    def cluster(number):
        return offset + (32 + number - 2) * 512

    def file_set(name, start, size, no_fat_chain=False):
        group = bytearray(96)
        group[0:2] = bytes((0x85, 2))
        struct.pack_into('<H', group, 4, 0x20)
        group[32:34] = bytes((0xC0, 3 if no_fat_chain else 1))
        group[35] = len(name)
        struct.pack_into('<Q', group, 40, size)
        struct.pack_into('<I', group, 52, start)
        struct.pack_into('<Q', group, 56, size)
        group[64] = 0xC1
        encoded = name.encode('utf-16le')
        group[66:66 + len(encoded)] = encoded
        checksum = 0
        for i, byte in enumerate(group):
            if i not in (2, 3):
                checksum = (((checksum & 1) << 15) + (checksum >> 1) + byte) & 0xFFFF
        struct.pack_into('<H', group, 2, checksum)
        return group

    # Two bitmap identifiers, as required for a two-FAT volume. Deleted-file
    # recovery remains conservatively unavailable with multiple bitmaps.
    for identifier, bitmap_cluster in ((0, 9), (1, 10)):
        row = bytearray(32)
        row[:2] = bytes((0x81, identifier))
        struct.pack_into('<I', row, 20, bitmap_cluster)
        struct.pack_into('<Q', row, 24, 15)
        start = cluster(2) + identifier * 32
        raw[start:start + 32] = row
        raw[cluster(bitmap_cluster):cluster(bitmap_cluster) + 15] = b'\xff' * 15
    start = cluster(2) + 64
    raw[start:start + 96] = file_set('chain.bin', 3, 1024, contiguous)
    # Nonzero ignorable entries force directory continuation through the FAT.
    for position in range(cluster(2) + 160, cluster(2) + 512, 32):
        raw[position] = 0xA0
    for number, payload in ((3, b'A' * 512), (4, b'X' * 512), (6, b'B' * 512),
                            (7, file_set('good.txt', 4, 4)),
                            (8, file_set('stale.txt', 4, 4))):
        raw[cluster(number):cluster(number) + len(payload)] = payload
    return raw


class ActiveExfatTests(unittest.TestCase):
    def test_fragmented_export_preview_and_directory_use_active_fat(self):
        for active, offset in ((0, 0), (1, 0), (1, 1024 * 1024)):
            with self.subTest(active=active, offset=offset), tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / 'source.img'
                source.write_bytes(dual_fat_image(active, offset))
                digest = hashlib.sha256(source.read_bytes()).digest()
                index = scan_tree(str(source), offset=offset)
                entries = index.list_dir(5)
                item = next(e for e in entries if e.name == 'chain.bin')
                expected = b'A' * 512 + (b'B' if active else b'X') * 512
                self.assertEqual(index.preview(str(source), item), expected)
                self.assertEqual({e.name for e in entries},
                                 {'chain.bin', 'good.txt' if active else 'stale.txt'})
                output = Path(tmp) / 'out'
                output.mkdir()
                report = export_selection(str(source), index, [item], str(output))
                self.assertEqual((report.exported, report.errors), (1, []))
                self.assertEqual((output / 'chain.bin').read_bytes(), expected)
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)

    def test_contiguous_stream_does_not_follow_fat_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.img'
            source.write_bytes(dual_fat_image(contiguous=True))
            index = scan_tree(str(source))
            item = next(e for e in index.list_dir(5) if e.name == 'chain.bin')
            self.assertEqual(index.preview(str(source), item), b'A' * 512 + b'X' * 512)

    def test_single_fat_cannot_select_second_fat(self):
        raw = dual_fat_image(active=1)
        raw[110] = 1
        with self.assertRaises(FileSystemError):
            ExFAT(io.BytesIO(raw), 0)

    def test_fat_region_must_not_overlap_cluster_heap(self):
        raw = dual_fat_image()
        struct.pack_into('<I', raw, 84, 5)  # FATs would end at sector 34; heap starts at 32.
        with self.assertRaises(FileSystemError):
            ExFAT(io.BytesIO(raw), 0)

    def test_single_fat_deleted_recovery_rejects_second_bitmap_identifier(self):
        from test_deleted_non_ntfs import make_exfat_image
        raw = bytearray(make_exfat_image())
        raw[32 * 512 + 1] = 1  # Only a second bitmap is described, but only FAT 0 exists.
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.img'
            source.write_bytes(raw)
            index = scan_tree(str(source))
            item = next(e for e in index.list_dir(5) if e.is_deleted)
            self.assertFalse(item.recoverable)

    def test_broken_or_cyclic_active_file_chain_does_not_export_successfully(self):
        for next_cluster in (0, 3):
            with self.subTest(next_cluster=next_cluster), tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / 'source.img'
                source.write_bytes(dual_fat_image(next_cluster=next_cluster))
                index = scan_tree(str(source))
                item = next(e for e in index.list_dir(5) if e.name == 'chain.bin')
                output = Path(tmp) / 'out'
                output.mkdir()
                report = export_selection(str(source), index, [item], str(output))
                self.assertEqual(report.exported, 0)
                self.assertTrue(report.errors)
                self.assertFalse((output / 'chain.bin').exists())


if __name__ == '__main__':
    unittest.main()
