"""Damage-tolerance tests on synthetic images, never user disks."""
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from test_browser import image_with_folders
from test_ntfs import CLUSTER, MFT_LCN, SIZE
from recoverydesk import ntfs_browser, filesystems
from recoverydesk.ntfs import NTFSError
from recoverydesk.scan_report import format_scan_report


class FaultyReader:
    """A read-only image reader that rejects requests crossing a specific byte range."""
    def __init__(self, raw, first, last):
        self.raw, self.first, self.last = raw, first, last
    def seek(self, *args):
        return self.raw.seek(*args)
    def tell(self):
        return self.raw.tell()
    def read(self, n=-1):
        pos = self.raw.tell()
        if n < 0:
            raise RuntimeError('Unexpected unlimited read')
        if pos < self.last and pos + n > self.first:
            raise OSError(5, 'Simulierter Lesefehler')
        return self.raw.read(n)


class ToleranceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / 'disk.raw')
        Path(self.path).write_bytes(image_with_folders())

    def test_corrupt_fixup_record_is_counted_without_hiding_other_files(self):
        raw = bytearray(Path(self.path).read_bytes())
        off = MFT_LCN * CLUSTER + 8 * SIZE
        raw[off + 510] = 0xff  # break FILE-record sector fixup
        Path(self.path).write_bytes(raw)
        result = ntfs_browser.scan_ntfs_tree(self.path)
        self.assertEqual(result.damaged_records, 1)
        self.assertEqual(result.unreadable_records, 0)
        self.assertIn('bericht.txt', [e.name for e in result.entries])
        self.assertNotIn('gelöscht.keine_endung', [e.name for e in result.entries])
        self.assertIn('Nicht auswertbare MFT-Datensätze: 1', format_scan_report(self.path, result))

    def test_salvage_skips_fault_only_and_keeps_neighbors(self):
        off = MFT_LCN * CLUSTER + 9 * SIZE
        original_opener = ntfs_browser.open_source
        @contextmanager
        def broken_open(path):
            with original_opener(path) as raw:
                yield FaultyReader(raw, off, off + SIZE)
        with patch.object(ntfs_browser, 'open_source', broken_open):
            with self.assertRaisesRegex(NTFSError, 'MFT-Lesefehler'):
                ntfs_browser.scan_ntfs_tree(self.path)
            result = ntfs_browser.scan_ntfs_tree(self.path, tolerate_read_errors=True)
        names = {e.name for e in result.entries}
        self.assertIn('bericht.txt', names)
        self.assertIn('gelöscht.keine_endung', names)
        self.assertIn('bild.irgendwas', names)
        self.assertNotIn('unterordner', names)
        self.assertEqual(result.unreadable_records, 1)
        self.assertTrue(any(start <= 9 <= end for start, end in result.read_error_ranges))
        self.assertTrue(result.tolerant)

    def test_device_rejected_in_tolerant_mode(self):
        with patch.object(ntfs_browser, 'is_device_source', return_value=True):
            with self.assertRaisesRegex(NTFSError, 'Image-Datei'):
                ntfs_browser.scan_ntfs_tree(r'\\.\PhysicalDrive1', tolerate_read_errors=True)

    def test_generic_unreadable_subdirectory_is_skipped(self):
        class FakeVolume:
            root_locator = (5,)
            label = 'FAT32'
            def list_directory(self, f, loc):
                if loc == (5,):
                    return [('beschädigt', True, 0, (6,), ''),
                            ('lesbar', True, 0, (7,), '')]
                if loc == (6,):
                    raise OSError(5, 'Simulierter Lesefehler')
                if loc == (7,):
                    return [('Datei ohne Endung', False, 3, (20,), '')]
                return []
        with patch.object(filesystems, 'detect_volume', return_value=FakeVolume()):
            with self.assertRaises(OSError):
                filesystems.scan_tree(self.path)
            result = filesystems.scan_tree(self.path, tolerate_read_errors=True)
        self.assertEqual(result.unreadable_directories, 1)
        self.assertEqual({e.name for e in result.entries}, {'beschädigt', 'lesbar', 'Datei ohne Endung'})
        self.assertIn('nicht lesbar', next(e for e in result.entries if e.name == 'beschädigt').unsupported_reason)
        self.assertIn('Nicht lesbare Unterordner: 1', format_scan_report(self.path, result))

    def test_generic_root_damage_remains_fatal(self):
        class Broken:
            root_locator = (5,)
            label = 'ext4'
            def list_directory(self, f, loc):
                raise OSError(5, 'Wurzelverzeichnis beschädigt')
        with patch.object(filesystems, 'detect_volume', return_value=Broken()):
            with self.assertRaises(OSError):
                filesystems.scan_tree(self.path, tolerate_read_errors=True)

    def test_generic_tolerant_mode_blocks_device(self):
        with patch.object(filesystems, 'is_device_source', return_value=True):
            with self.assertRaisesRegex(filesystems.FileSystemError, 'nur für Images'):
                filesystems.scan_tree(r'\\.\PhysicalDrive2', tolerate_read_errors=True)


if __name__ == '__main__':
    unittest.main()
