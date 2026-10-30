"""Read-only pre-export verification regression tests."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from recoverydesk.file_verification import (verify_file, VerificationError,
                                           VerificationCancelled, MAX_VERIFY_BYTES)
from recoverydesk.ntfs_browser import scan_ntfs_tree, FileEntry
from recoverydesk.filesystems import scan_tree
from test_browser import image_with_folders
from test_filesystems import fat_img, exfat_img, ext4_img


class VerificationTests(unittest.TestCase):
    def test_ntfs_resident_and_deleted_file_check(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'disk.raw'
            original = image_with_folders()
            path.write_bytes(original)
            index = scan_ntfs_tree(str(path))
            for item, expected in [('bericht.txt', b'FIRST'), ('gelöscht.keine_endung', b'RECOVER')]:
                entry = next(e for e in index.list_dir(6) if e.name == item)
                events = []
                result = verify_file(str(path), index, entry, filesystem='NTFS', progress=events.append)
                self.assertTrue(result.complete)
                self.assertEqual(result.read_bytes, len(expected))
                self.assertEqual(result.sha256, hashlib.sha256(expected).hexdigest())
                self.assertIn('beweist weder', result.message)
                self.assertEqual(events[-1], len(expected))
            self.assertEqual(path.read_bytes(), original)

    def test_ntfs_nonresident_fragmented_and_uninitialized_tail(self):
        import struct
        from recoverydesk.ntfs import DataRun, parse_boot_sector
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'runs.raw'
            raw = bytearray(512 * 128)
            boot = bytearray(512)
            boot[3:11] = b'NTFS    '
            struct.pack_into('<H', boot, 11, 512)
            boot[13] = 1
            struct.pack_into('<Q', boot, 40, 128)
            struct.pack_into('<Q', boot, 48, 4)
            struct.pack_into('<b', boot, 64, -10)
            boot[510:512] = b'\x55\xaa'
            raw[:512] = boot
            raw[20*512:21*512] = b'A' * 512
            raw[34*512:35*512] = b'B' * 512
            path.write_bytes(raw)
            with path.open('rb') as f:
                info = parse_boot_sector(f)
            item = FileEntry(15, 1, 'fragment.bin', 5, 1, False, False,
                             size=1200, data_kind='nonresident', initialized_size=1000,
                             data_runs=[DataRun(20, 1), DataRun(34, 1)])
            expected = b'A' * 512 + b'B' * 488 + bytes(200)
            result = verify_file(str(path), SimpleNamespace(info=info), item,
                                 filesystem='NTFS')
            self.assertEqual(result.read_bytes, 1200)
            self.assertEqual(result.sha256, hashlib.sha256(expected).hexdigest())

    def test_fat_exfat_ext4_read_stream(self):
        cases = [('FAT32', fat_img(), 'README.TXT', b'HELLO'),
                 ('exFAT', exfat_img(), 'notes.log', b'EXFAT!!'),
                 ('ext4', ext4_img(), 'report.any', b'HELLOext4')]
        with tempfile.TemporaryDirectory() as td:
            for name, contents, filename, expected in cases:
                with self.subTest(name=name):
                    path = Path(td) / (name + '.raw')
                    path.write_bytes(contents)
                    index = scan_tree(str(path))
                    entry = next(e for e in index.list_dir(5) if e.name == filename)
                    result = verify_file(str(path), index, entry, filesystem=index.filesystem)
                    self.assertEqual(result.expected_bytes, len(expected))
                    self.assertEqual(result.sha256, hashlib.sha256(expected).hexdigest())
                    self.assertEqual(path.read_bytes(), contents)

    def test_inconsistent_resident_length_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'disk.raw'
            path.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(path))
            e = next(e for e in index.list_dir(6) if e.name == 'bericht.txt')
            e.size += 2
            with self.assertRaisesRegex(VerificationError, 'Inkonsistenter'):
                verify_file(str(path), index, e, filesystem='NTFS')

    def test_short_non_ntfs_read_fails(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'fat.raw'
            path.write_bytes(fat_img())
            index = scan_tree(str(path))
            entry = next(e for e in index.list_dir(5) if e.name == 'README.TXT')
            previous = index.volumes.iter_file
            index.volumes.iter_file = lambda _f, _entry, max_bytes=None: iter([b'X'])
            try:
                with self.assertRaisesRegex(VerificationError, 'unvollständig'):
                    verify_file(str(path), index, entry, filesystem=index.filesystem)
            finally:
                index.volumes.iter_file = previous

    def test_read_overflow_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'fat.raw'
            path.write_bytes(fat_img())
            index = scan_tree(str(path))
            entry = next(e for e in index.list_dir(5) if e.name == 'README.TXT')
            previous = index.volumes.iter_file
            index.volumes.iter_file = lambda _f, _entry, max_bytes=None: iter([b'OVERFLOW'])
            try:
                with self.assertRaisesRegex(VerificationError, 'überschreitet'):
                    verify_file(str(path), index, entry, filesystem=index.filesystem)
            finally:
                index.volumes.iter_file = previous

    def test_cancel_before_and_during_read(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'fat.raw'
            path.write_bytes(fat_img())
            index = scan_tree(str(path))
            entry = next(e for e in index.list_dir(5) if e.name == 'README.TXT')
            with self.assertRaises(VerificationCancelled):
                verify_file(str(path), index, entry, filesystem=index.filesystem, cancel=lambda: True)
            interrupted = {'yes':False}
            with self.assertRaises(VerificationCancelled):
                verify_file(str(path), index, entry, filesystem=index.filesystem,
                    cancel=lambda: interrupted['yes'],
                    progress=lambda n: interrupted.__setitem__('yes',True))

    def test_limit_and_nonrecoverable_block(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'fat.raw'
            path.write_bytes(fat_img())
            index = scan_tree(str(path))
            entry = next(e for e in index.list_dir(5) if e.name == 'README.TXT')
            with self.assertRaisesRegex(VerificationError, 'zu groß'):
                verify_file(str(path), index, entry, filesystem=index.filesystem, max_bytes=4)
            folder = next(e for e in index.list_dir(5) if e.is_directory)
            with self.assertRaisesRegex(VerificationError, 'keinen unterstützten'):
                verify_file(str(path), index, folder, filesystem=index.filesystem)
            self.assertEqual(MAX_VERIFY_BYTES, 512 * 1024 * 1024)


class VerificationGuiTests(unittest.TestCase):
    def test_accent_button_and_inspection_controls(self):
        from recoverydesk.gui import RecoveryDeskApp
        app = RecoveryDeskApp()
        app.withdraw()
        try:
            self.assertEqual(len(app.tabs.tabs()), 3)
            self.assertEqual(app.export_button.cget('background'), app._palette()['accent'])
            self.assertEqual(app.export_button.cget('foreground'), app._palette()['accent_text'])
            self.assertEqual(app.export_button.cget('text'), 'Stapel-Export / fortsetzen')
            self.assertTrue(callable(app.inspect_file))
        finally:
            app.destroy()
