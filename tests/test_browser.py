"""MFT directory enumeration and exports, tested only on synthetic NTFS images."""
import os
import tempfile
from pathlib import Path
import struct
import unittest
from test_ntfs import make_image, file_record, resident_attr, nonresident_attr, CLUSTER, MFT_LCN, SIZE
from recoverydesk.ntfs_browser import (scan_ntfs_tree, export_selection, export_file, safe_name,
                                        FileEntry, ROOT_RECORD, ORPHANS, ScanCancelled)


def filename(name, parent, parent_sequence=0, namespace=1):
    encoded = name.encode('utf-16le')
    value = bytearray(66 + len(encoded))
    struct.pack_into('<Q', value, 0, (parent_sequence << 48) | parent)
    value[64], value[65] = len(encoded)//2, namespace
    value[66:] = encoded
    return resident_attr(0x30, value)


def record(attrs, flags=1, sequence=1):
    buf = bytearray(file_record(attrs, in_use=bool(flags & 1)))
    struct.pack_into('<H', buf, 22, flags)
    struct.pack_into('<H', buf, 16, sequence)
    return bytes(buf)


def image_with_folders(base=0):
    raw = bytearray(make_image(base))
    def install(n, data):
        start = base + MFT_LCN*CLUSTER + n*SIZE
        raw[start:start+SIZE] = data
    install(5, record([filename('Wurzel', 5)], flags=3))
    install(6, record([filename('Dokumente', 5)], flags=3))
    install(7, record([filename('bericht.txt', 6), resident_attr(0x80, b'FIRST')], flags=1))
    # extend $MFT in fixture from 16 to 24 clusters to hold 12 records
    stream = nonresident_attr(0x80, b'\x11\x18\x04\x00', 24*CLUSTER, 23)
    install(0, file_record([stream], in_use=True))
    install(8, record([filename('gelöscht.keine_endung', 6), resident_attr(0x80, b'RECOVER')], flags=0))
    install(9, record([filename('unterordner', 6)], flags=3))
    install(10, record([filename('bild.irgendwas', 9), resident_attr(0x80, b'NOT-A-JPEG')], flags=1))
    install(11, record([filename('orphan.dat', 1729), resident_attr(0x80, b'ORPHAN')], flags=1))
    return bytes(raw)


class BrowserTests(unittest.TestCase):
    def test_every_file_type_and_folders(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'input.raw'
            path.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(path))
            roots = index.list_dir(ROOT_RECORD)
            self.assertIn('Dokumente', [x.name for x in roots])
            children = index.list_dir(6)
            self.assertEqual({x.name for x in children}, {'bericht.txt', 'gelöscht.keine_endung', 'unterordner'})
            self.assertEqual([x.name for x in index.list_dir(6, show_deleted=False)], ['unterordner', 'bericht.txt'])
            self.assertEqual([x.name for x in index.list_dir(9)], ['bild.irgendwas'])
            self.assertEqual([x.name for x in index.list_dir(ORPHANS)], ['orphan.dat'])
            self.assertEqual(index.orphan_count, 1)
            self.assertTrue(next(x for x in children if x.name == 'gelöscht.keine_endung').is_deleted)
            self.assertTrue(next(x for x in children if x.name == 'bericht.txt').recoverable)
            self.assertEqual(index.total_records, 12)

    def test_recursive_export_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'input.raw'
            path.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(path))
            folder = next(x for x in index.list_dir(5) if x.name == 'Dokumente')
            outdir = Path(td)/'rescued'
            outdir.mkdir()
            first = export_selection(str(path), index, [folder], str(outdir))
            self.assertEqual(first.directories, 2)
            self.assertEqual(first.exported, 3)
            self.assertEqual((outdir/'Dokumente'/'bericht.txt').read_bytes(), b'FIRST')
            self.assertEqual((outdir/'Dokumente'/'gelöscht.keine_endung').read_bytes(), b'RECOVER')
            self.assertEqual((outdir/'Dokumente'/'unterordner'/'bild.irgendwas').read_bytes(), b'NOT-A-JPEG')
            again = export_selection(str(path), index, [folder], str(outdir))
            self.assertEqual(again.exported, 3)
            self.assertTrue((outdir/'Dokumente__MFT6_0'/'bericht.txt').exists())
            original = (outdir/'Dokumente'/'bericht.txt').read_bytes()
            self.assertEqual(original, b'FIRST')
            self.assertEqual(path.read_bytes(), image_with_folders())

    def test_bad_names_and_cancel(self):
        self.assertEqual(safe_name('../CON', 11), '_CON')
        self.assertEqual(safe_name('nul.txt', 3), '_nul.txt')
        self.assertEqual(safe_name('../a\\b', 10), '_a_b')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'input.raw'
            path.write_bytes(image_with_folders())
            with self.assertRaises(ScanCancelled):
                scan_ntfs_tree(str(path), cancel=lambda: True)

    def test_hardlinks_and_reused_parent_record(self):
        with tempfile.TemporaryDirectory() as td:
            raw = bytearray(image_with_folders())
            start = MFT_LCN * CLUSTER + 7*SIZE
            raw[start:start+SIZE] = record([
                filename('zwei.txt', 5), filename('eins.txt', 6),
                resident_attr(0x80, b'TWO-HARDLINKS')], flags=1)
            bad_start = MFT_LCN * CLUSTER + 11*SIZE
            raw[bad_start:bad_start+SIZE] = record([
                filename('nicht_hier.txt', 6, parent_sequence=999),
                resident_attr(0x80, b'MISPLACED')], flags=1)
            path = Path(td) / 'hardlinks.raw'
            path.write_bytes(raw)
            index = scan_ntfs_tree(str(path))
            self.assertIn('eins.txt', [x.name for x in index.list_dir(6)])
            self.assertIn('zwei.txt', [x.name for x in index.list_dir(5)])
            self.assertIn('nicht_hier.txt', [x.name for x in index.list_dir(ORPHANS)])
            self.assertNotIn('nicht_hier.txt', [x.name for x in index.list_dir(6)])
            entry = next(x for x in index.list_dir(5) if x.name == 'zwei.txt')
            saved = Path(td) / 'saved.txt'
            export_file(str(path), index.info, entry, str(saved))
            self.assertEqual(saved.read_bytes(), b'TWO-HARDLINKS')

    def test_volume_with_partition_offset(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'disk.raw'
            offset = 1024*1024
            path.write_bytes(image_with_folders(offset))
            index = scan_ntfs_tree(str(path), partition_offset=offset)
            self.assertEqual(index.info.partition_offset, offset)
            self.assertIn('Dokumente', [e.name for e in index.list_dir(5)])


if __name__ == '__main__':
    unittest.main()
