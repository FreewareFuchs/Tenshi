"""FAT32 ExtFlags must select the authoritative chain, even when both look valid."""
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import unittest

from recoverydesk.filesystems import FAT32, FileSystemError, scan_tree, export_selection


def active_fat_image(flags=0x81, offset=0):
    # FAT32-sized geometry, with distinct but equally long file and directory chains.
    bps, reserved, fat_sectors, sectors = 512, 32, 524, 67000
    raw = bytearray(offset + bps * sectors)
    raw[offset:offset + 3] = b'\xeb\x58\x90'
    raw[offset + 82:offset + 90] = b'FAT32   '
    raw[offset + 510:offset + 512] = b'\x55\xaa'
    struct.pack_into('<H', raw, offset + 11, bps)
    raw[offset + 13] = 1
    struct.pack_into('<H', raw, offset + 14, reserved)
    raw[offset + 16] = 2
    for position, value in ((32, sectors), (36, fat_sectors), (44, 2)):
        struct.pack_into('<I', raw, offset + position, value)
    struct.pack_into('<H', raw, offset + 40, flags)
    for copy, file_next, root_next in ((0, 4, 8), (1, 6, 7)):
        base = offset + (reserved + copy * fat_sectors) * bps
        for cluster, value in ((0, 0x0FFFFFF8), (1, 0xFFFFFFFF), (2, root_next),
                               (3, file_next), (4, 0x0FFFFFFF), (6, 0x0FFFFFFF),
                               (7, 0x0FFFFFFF), (8, 0x0FFFFFFF),
                               (9, 0x0FFFFFFF), (10, 0x0FFFFFFF)):
            struct.pack_into('<I', raw, base + cluster * 4, value)
    data = offset + (reserved + 2 * fat_sectors) * bps

    def entry(name, cluster, size, attr=0x20):
        row = bytearray(32)
        row[:11] = name
        row[11] = attr
        struct.pack_into('<H', row, 26, cluster)
        struct.pack_into('<I', row, 28, size)
        return row

    # No end marker in the first directory cluster: traversal must consult the FAT.
    raw[data:data + 512] = (entry(b'CHAIN   BIN', 3, 1024) +
                           entry(b'PADDING    ', 0, 0, attr=0x08) * 15)
    for cluster, payload in ((3, b'A' * 512), (4, b'X' * 512), (6, b'B' * 512),
                              (7, entry(b'GOOD    TXT', 9, 4)),
                              (8, entry(b'BAD     TXT', 10, 4)),
                              (9, b'GOOD'), (10, b'BAD!')):
        start = data + (cluster - 2) * bps
        raw[start:start + len(payload)] = payload
    return raw


class ActiveFatTests(unittest.TestCase):
    def test_second_fat_export_and_preview_use_correct_content_at_equal_size(self):
        for offset in (0, 1024 * 1024):
            with self.subTest(offset=offset), tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp) / 'source.raw'
                source.write_bytes(active_fat_image(offset=offset))
                digest = hashlib.sha256(source.read_bytes()).digest()
                index = scan_tree(str(source), offset=offset)
                item = next(e for e in index.list_dir(5) if e.name == 'CHAIN.BIN')
                expected = b'A' * 512 + b'B' * 512
                self.assertEqual(index.preview(str(source), item), expected)
                output = Path(tmp) / 'out'
                output.mkdir()
                report = export_selection(str(source), index, [item], str(output))
                self.assertEqual(report.exported, 1, report.errors)
                self.assertEqual(report.errors, [])
                actual = (output / 'CHAIN.BIN').read_bytes()
                self.assertEqual(len(actual), 1024)
                self.assertEqual(actual, expected)
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)

    def test_directory_continuation_uses_second_fat(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.raw'
            source.write_bytes(active_fat_image())
            index = scan_tree(str(source))
            self.assertEqual({e.name for e in index.list_dir(5)}, {'CHAIN.BIN', 'GOOD.TXT'})

    def test_first_fat_selected_and_index_ignored_when_mirroring_enabled(self):
        for flags in (0x80, 0x00, 0x01, 0x0F):
            with self.subTest(flags=flags):
                stream = io.BytesIO(active_fat_image(flags))
                volume = FAT32(stream, 0)
                self.assertEqual(list(volume.clusters(stream, 3)), [3, 4])

    def test_invalid_active_fat_rejected_instead_of_falling_back(self):
        for flags, fats in ((0x82, 2), (0x8F, 2), (0x81, 1)):
            with self.subTest(flags=flags, fats=fats):
                raw = active_fat_image(flags)
                raw[16] = fats
                with self.assertRaises(FileSystemError):
                    FAT32(io.BytesIO(raw), 0)


if __name__ == '__main__':
    unittest.main()
