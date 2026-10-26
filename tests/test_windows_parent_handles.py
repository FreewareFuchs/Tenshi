"""Windows-native junction/race checks plus portable Win32 flag regressions."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from recoverydesk import secure_target, windows_target


class WindowsOpenFlagsTests(unittest.TestCase):
    def api(self, attributes):
        api = object.__new__(windows_target._API)
        api.create = mock.Mock(return_value=123)
        api.close = mock.Mock()
        def info(handle, pointer):
            ctypes.cast(pointer, ctypes.POINTER(windows_target._FileInfo)).contents.attributes = attributes
            return True
        api.info = info
        return api

    def test_parent_opens_reparse_point_itself_and_denies_write_delete(self):
        api = self.api(0x10)
        self.assertEqual(api.open('parent', directory=True), 123)
        args = api.create.call_args.args
        self.assertEqual(args[1:3], (0x80, 1))
        self.assertEqual(args[4], 3)  # OPEN_EXISTING
        self.assertEqual(args[5], 0x02200000)  # BACKUP_SEMANTICS|OPEN_REPARSE_POINT
        api.close.assert_not_called()

    def test_reparse_handle_is_rejected_and_closed(self):
        api = self.api(0x410)
        with self.assertRaisesRegex(ValueError, 'Junctions'):
            api.open('junction', directory=True)
        api.close.assert_called_once_with(123)

    def test_final_directory_cannot_be_used_as_file(self):
        api = self.api(0x10)
        with self.assertRaisesRegex(ValueError, 'Dateityp'):
            api.open('directory')
        api.close.assert_called_once_with(123)

    def test_file_open_never_truncates_or_allows_delete(self):
        for mode, disposition in [('xb', 1), ('r+b', 3)]:
            with self.subTest(mode=mode):
                api = self.api(0x80)
                api.open('file', mode=mode)
                args = api.create.call_args.args
                self.assertEqual(args[2], 1)
                self.assertEqual(args[4], disposition)
                self.assertTrue(args[5] & 0x00200000)


@unittest.skipUnless(sys.platform == 'win32', 'Native Windows handle sharing')
class WindowsParentHandleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.raw'
        self.source.write_bytes(b'original source')
        self.parent = self.root / 'output'
        self.parent.mkdir()

    def output(self, path, mode='xb'):
        return secure_target.open_regular_output(str(path), mode, str(self.source))

    def junction(self, path, target):
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(path), str(target)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_parent_and_ancestor_cannot_be_renamed_until_output_closes(self):
        nested = self.parent / 'nested'
        nested.mkdir()
        with self.output(nested / 'file.bin') as out:
            for parent in [nested, self.parent]:
                with self.subTest(parent=parent):
                    with self.assertRaises(OSError):
                        parent.rename(parent.with_name(parent.name + '-moved'))
            out.write(b'correct')
        self.assertEqual((nested / 'file.bin').read_bytes(), b'correct')
        self.parent.rename(self.root / 'released')
        self.assertEqual(self.source.read_bytes(), b'original source')

    def test_existing_junction_never_creates_file_outside_target(self):
        outside = self.root / 'outside'
        outside.mkdir()
        link = self.parent / 'junction'
        self.junction(link, outside)
        try:
            with self.assertRaisesRegex(ValueError, 'Junctions'):
                with self.output(link / 'foreign.bin'):
                    self.fail('junction accepted')
            self.assertFalse((outside / 'foreign.bin').exists())
        finally:
            os.rmdir(link)
        # All earlier directory handles also close after the rejection.
        self.parent.rename(self.root / 'released')

    def test_final_symlink_does_not_open_source_for_writing(self):
        link = self.parent / 'alias.img'
        try:
            link.symlink_to(self.source)
        except OSError as exc:
            if getattr(exc, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege unavailable')
            raise
        with self.assertRaisesRegex(ValueError, 'Junctions'):
            with self.output(link, 'r+b'):
                self.fail('symlink accepted')
        self.assertEqual(self.source.read_bytes(), b'original source')

    def test_writer_and_leaf_replacement_blocked_while_open(self):
        path = self.parent / 'file.bin'
        with self.output(path) as out:
            out.write(b'preserve')
            with self.assertRaises(OSError):
                with path.open('r+b'):
                    self.fail('second writer accepted')
            with self.assertRaises(OSError):
                path.unlink()
        self.assertEqual(path.read_bytes(), b'preserve')
        path.unlink()

    def test_existing_file_is_not_truncated_and_open_failure_releases_parents(self):
        path = self.parent / 'file.bin'
        path.write_bytes(b'preserve')
        with self.output(path, 'r+b') as out:
            self.assertEqual(out.read(), b'preserve')
        with self.assertRaises(OSError):
            with self.output(path):
                self.fail('exclusive create replaced a file')
        self.assertEqual(path.read_bytes(), b'preserve')
        self.parent.rename(self.root / 'released')
