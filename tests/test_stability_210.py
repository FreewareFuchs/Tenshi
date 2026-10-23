"""Regression tests for atomic checkpoints, Windows sharing locks and diagnostics."""
import errno
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.resilience import atomic_replace_json
from recoverydesk.diagnostics import log_issue, diagnostic_log_path
from recoverydesk.imaging import create_image, ImagingError
from recoverydesk.batch_export import export_batch, MANIFEST
from recoverydesk.ntfs_browser import scan_ntfs_tree
from test_browser import image_with_folders


class ReliableCheckpointTests(unittest.TestCase):
    def test_retry_when_windows_sharing_lock_is_transient(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'manifest.json'
            target.write_text('{"status":"old"}')
            calls = []
            def flaky(src, dst):
                calls.append((src, dst))
                if len(calls) < 3:
                    raise PermissionError(errno.EACCES, 'simulated windows sharing violation')
                return os.replace(src, dst)
            atomic_replace_json(target, {'status': 'new'}, replace=flaky, sleep=lambda _: None)
            self.assertEqual(json.loads(target.read_text())['status'], 'new')
            self.assertEqual(len(calls), 3)
            self.assertEqual(len(list(Path(td).glob('.tenshi-checkpoint*'))), 0)

    def test_permanent_lock_preserves_previous_status_and_removes_private_temp(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'status.json'
            original = '{"a": 1}'
            target.write_text(original)
            with self.assertRaises(PermissionError):
                atomic_replace_json(target, {'a': 2},
                    replace=lambda src, dst: (_ for _ in ()).throw(PermissionError(errno.EACCES, 'locked')),
                    sleep=lambda _: None)
            self.assertEqual(target.read_text(), original)
            self.assertEqual(list(Path(td).glob('.tenshi-checkpoint*')), [])

    def test_unrelated_write_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as td:
            calls = []
            def fail(src, dst):
                calls.append(1)
                raise OSError(errno.ENOSPC, 'full disk')
            with self.assertRaises(OSError):
                atomic_replace_json(Path(td) / 'check.json', {'a': 1}, replace=fail,
                                    sleep=lambda _: self.fail('should not wait'))
            self.assertEqual(len(calls), 1)

    def test_old_temp_file_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            old = folder / 'recoverydesk_status.json.tmp'
            old.write_bytes(b'OTHER FILE')
            target = folder / 'recoverydesk_status.json'
            atomic_replace_json(target, {'ok': True})
            self.assertEqual(old.read_bytes(), b'OTHER FILE')
            self.assertTrue(json.loads(target.read_text())['ok'])

    def test_refuse_symlink_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            other = Path(td) / 'other.txt'
            other.write_text('KEEP')
            link = Path(td) / 'link.json'
            try:
                link.symlink_to(other)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks not allowed on this test host')
            with self.assertRaises(ValueError):
                atomic_replace_json(link, {'unsafe': True})
            self.assertEqual(other.read_text(), 'KEEP')

    def test_batch_status_file_stays_resumeable_with_stale_legacy_tmp(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / 'disk.raw'
            src.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(src))
            folder = next(x for x in index.list_dir(5) if x.name == 'Dokumente')
            output = d / 'rescued'
            output.mkdir()
            first = export_batch(str(src), index, [folder], str(output))
            stale = Path(first.root) / (MANIFEST + '.tmp')
            stale.write_bytes(b'PREEXISTING')
            second = export_batch(str(src), index, [folder], str(output))
            self.assertEqual(second.verified_existing, 3)
            self.assertEqual(stale.read_bytes(), b'PREEXISTING')

    def test_batch_retry_transient_lock_is_integrated(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            src = d / 'disk.raw'
            src.write_bytes(image_with_folders())
            index = scan_ntfs_tree(str(src))
            folder = next(x for x in index.list_dir(5) if x.name == 'Dokumente')
            output = d / 'rescued'
            output.mkdir()
            orig_replace = os.replace
            count = [0]
            def flaky_replace(src_, dst_, **kwargs):
                if str(dst_).endswith(MANIFEST) and count[0] < 2:
                    count[0] += 1
                    raise PermissionError(errno.EACCES, 'sharing violation')
                return orig_replace(src_, dst_, **kwargs)
            with patch('recoverydesk.resilience.os.replace', side_effect=flaky_replace):
                result = export_batch(str(src), index, [folder], str(output))
            self.assertEqual(result.exported, 3)
            self.assertEqual(count[0], 2)
            self.assertTrue(Path(result.manifest).is_file())

    def test_imaging_failure_reports_operation_only_without_filename(self):
        with tempfile.TemporaryDirectory() as td:
            log_dir = Path(td) / 'diagnostics'
            with patch.dict(os.environ, {'TENSHI_LOG_DIR': str(log_dir)}):
                try:
                    create_image(str(Path(td) / 'sensitive-private-file.raw'),
                                 str(Path(td) / 'target.img'))
                except ValueError:
                    pass
                except OSError:
                    pass
                else:
                    self.fail('missing source must raise')
                output = (log_dir / 'tenshi-errors.log').read_text()
                self.assertIn('operation=imaging', output)
                self.assertNotIn('sensitive-private-file.raw', output)
                self.assertNotIn('target.img', output)

    def test_logfile_is_closed_between_records_for_windows_cleanup(self):
        """Temporary diagnostic folders must remain removable on Windows."""
        from recoverydesk import diagnostics
        with tempfile.TemporaryDirectory() as td:
            log_dir = Path(td) / 'diagnostics'
            with patch.dict(os.environ, {'TENSHI_LOG_DIR': str(log_dir)}):
                log_issue('simulated_failure', ValueError('do not log this path'))
                expected = log_dir / 'tenshi-errors.log'
                self.assertTrue(expected.is_file())
                handlers = [h for h in diagnostics._LOG.handlers
                            if isinstance(h, diagnostics.ClosingRotatingFileHandler)]
                self.assertEqual(len(handlers), 1)
                self.assertIsNone(handlers[0].stream)
                self.assertIn('operation=simulated_failure', expected.read_text())
                # Works on Windows too only if no handler has the file open.
                renamed = log_dir / 'archived.log'
                expected.rename(renamed)
                self.assertTrue(renamed.is_file())
                log_issue('another_failure', OSError('test'))
                self.assertTrue(expected.is_file())
                self.assertIsNone(handlers[0].stream)
        # On Windows TemporaryDirectory cleanup would raise WinError 32 if open.

    def test_logger_handles_readonly_log_directory(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td) / 'block'
            parent.write_text('this is not a directory')
            with patch.dict(os.environ, {'TENSHI_LOG_DIR': str(parent)}):
                log_issue('test_io', PermissionError('SensitiveFile.docx'))

    def test_aligned_device_read_is_readonly(self):
        import io
        from recoverydesk.sources import AlignedDeviceReader
        buf = io.BytesIO(bytes(range(256))*32)
        reader = AlignedDeviceReader(buf, 8192, 4096)
        self.assertFalse(reader.writable())
        reader.seek(13)
        self.assertEqual(reader.read(11), buf.getvalue()[13:24])
        self.assertFalse(hasattr(reader, 'write'))

if __name__ == '__main__':
    unittest.main()

class DeviceFailureHandlingTests(unittest.TestCase):
    def test_access_denied_is_not_marked_as_bad_sector(self):
        from recoverydesk.imaging import _recover_read, ImagingError
        class Reader:
            def seek(self, offset): pass
            def read(self, count): raise PermissionError(errno.EACCES, 'disk locked')
        failures = []
        with self.assertRaises(ImagingError):
            _recover_read(Reader(), 0, 4096, 4096, failures)
        self.assertEqual(failures, [])

    def test_short_device_read_aborts_without_zero_fill(self):
        from recoverydesk.imaging import _recover_read, ImagingError
        class Reader:
            def seek(self, offset): pass
            def read(self, count): return b''
        failures = []
        with self.assertRaises(ImagingError):
            _recover_read(Reader(), 0, 8192, 4096, failures, strict_short_read=True)
        self.assertEqual(failures, [])

    def test_actual_media_eio_still_produces_bad_range(self):
        from recoverydesk.imaging import _recover_read
        class Reader:
            def seek(self, offset): pass
            def read(self, count): raise OSError(errno.EIO, 'damaged media')
        failures = []
        self.assertEqual(_recover_read(Reader(), 0, 4096, 4096, failures), bytes(4096))
        self.assertEqual(failures, [[0, 4096]])

    def test_invalid_alignment_error_fails_closed(self):
        from recoverydesk.imaging import _recover_read, ImagingError
        class Reader:
            def seek(self, offset): pass
            def read(self, count): raise OSError(errno.EINVAL, 'invalid alignment')
        failures = []
        with self.assertRaises(ImagingError):
            _recover_read(Reader(), 0, 4096, 4096, failures)
        self.assertEqual(failures, [])

class WindowsInterfaceTests(unittest.TestCase):
    def test_device_access_denied_explains_admin_and_does_not_write(self):
        from recoverydesk.sources import open_source
        import recoverydesk.sources as sources
        with patch.object(sources, 'validate_source', return_value=r'\\.\PhysicalDrive1'), \
             patch.object(sources, 'is_device_source', return_value=True), \
             patch('builtins.open', side_effect=PermissionError(errno.EACCES, 'private path')) as fake_open:
            with self.assertRaisesRegex(PermissionError, 'Administratorrechte'):
                with open_source(r'\\.\PhysicalDrive1'):
                    pass
            self.assertTrue(any(call.args[1] == 'rb' for call in fake_open.call_args_list))

    def test_error_log_gui_opens_without_previous_errors(self):
        from recoverydesk.gui import RecoveryDeskApp
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'TENSHI_LOG_DIR': td,
                                                       'TENSHI_SETTINGS_FILE': str(Path(td) / 'settings.json')}):
            app = RecoveryDeskApp()
            try:
                app.withdraw()
                app.show_error_log()
                app.update_idletasks()
                self.assertTrue(app.error_log_button.winfo_exists())
                self.assertEqual(len(app.tabs.tabs()), 2)
            finally:
                app.destroy()
